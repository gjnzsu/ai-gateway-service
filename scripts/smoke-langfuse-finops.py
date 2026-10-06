"""Bounded metadata-only Langfuse observation check for an already executed run."""
import argparse
import json
import os
import re
import subprocess
import time

import httpx


TRACE_ID = re.compile(r"[0-9a-f]{32}\Z")


def local_storage_summary(trace_id):
    """Use the isolated stack when the backend cannot expand observation fields."""
    if not TRACE_ID.fullmatch(trace_id):
        raise SystemExit("trace ID must be 32 lowercase hexadecimal characters")
    query = f"""SELECT
count() AS generations,
countIf(input = '' AND output = '') AS content_free,
countIf(arrayElement(metadata_values, indexOf(metadata_names, 'cost_status')) = 'known'
  AND mapContains(provided_cost_details, 'total') AND provided_cost_details['total'] > 0) AS known_priced,
countIf(arrayElement(metadata_values, indexOf(metadata_names, 'cost_status')) = 'unknown'
  AND provided_model_name = '' AND length(provided_cost_details) = 0) AS unknown_unpriced
FROM events_full WHERE trace_id = '{trace_id}' AND type = 'GENERATION' FORMAT JSONEachRow"""
    command = [
        "docker", "compose", "--env-file", ".env.finops", "-f",
        "docker-compose.langfuse.yml", "exec", "-T", "clickhouse",
        "clickhouse-client", "--query", query,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise SystemExit("expanded observation API unavailable and local storage check failed") from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_id")
    parser.add_argument("--expected-generations", type=int, required=True)
    parser.add_argument("--deadline-seconds", type=float, default=20)
    args = parser.parse_args()
    base = os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3300").rstrip("/")
    auth = (os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"])
    deadline = time.monotonic() + args.deadline_seconds
    observations = []
    with httpx.Client(timeout=5) as client:
        while time.monotonic() < deadline:
            response = client.get(
                f"{base}/api/public/v2/observations",
                params={"traceId": args.trace_id, "fields": "core,basic,metadata,model,usage,io", "limit": 100},
                auth=auth,
            )
            if response.status_code == 502:
                summary = local_storage_summary(args.trace_id)
                if summary["generations"] != args.expected_generations:
                    raise SystemExit(
                        f"expected {args.expected_generations} generations, observed {summary['generations']}"
                    )
                if summary["content_free"] != summary["generations"]:
                    raise SystemExit("prompt or response content was exported")
                if summary["known_priced"] + summary["unknown_unpriced"] != summary["generations"]:
                    raise SystemExit("generation cost state is incomplete or unsafe")
                print(
                    f"verified {summary['generations']} metadata-only generations for trace "
                    f"{args.trace_id} (local storage fallback)"
                )
                return
            response.raise_for_status()
            observations = response.json().get("data", [])
            generations = [item for item in observations if item.get("type") == "GENERATION"]
            if len(generations) >= args.expected_generations:
                break
            time.sleep(0.25)
    generations = [item for item in observations if item.get("type") == "GENERATION"]
    if len(generations) != args.expected_generations:
        raise SystemExit(f"expected {args.expected_generations} generations, observed {len(generations)}")
    for item in generations:
        if item.get("input") not in (None, "") or item.get("output") not in (None, ""):
            raise SystemExit("prompt or response content was exported")
        metadata = item.get("metadata") or {}
        if metadata.get("cost_status") == "known" and not (item.get("costDetails") or {}).get("total"):
            raise SystemExit("known-cost generation has no explicit total")
        if metadata.get("cost_status") == "unknown" and (item.get("model") or item.get("costDetails")):
            raise SystemExit("unknown-cost generation enabled automatic or explicit pricing")
    print(f"verified {len(generations)} metadata-only generations for trace {args.trace_id}")


if __name__ == "__main__":
    main()
