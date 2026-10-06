from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _compose():
    return yaml.safe_load((ROOT / "docker-compose.langfuse.yml").read_text(encoding="utf-8"))


def test_langfuse_stack_is_isolated_and_pins_core_images():
    compose = _compose()
    services = compose["services"]
    assert set(services) == {"langfuse-web", "langfuse-worker", "postgres", "clickhouse", "redis", "minio"}
    assert services["langfuse-web"]["image"] == "docker.langfuse.com/langfuse/langfuse@sha256:3d2ae888a0e6edb41fdba6e7d5baca5e4baede3a870dac7970dadd9d925b018e"
    assert services["langfuse-worker"]["image"] == "docker.langfuse.com/langfuse/langfuse-worker@sha256:52f7fd41ded2f1a6acab13ff7cb1832d36dfe2cbf44adea402b7a09cfa4ce800"
    assert services["postgres"]["image"] == "postgres@sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f"
    assert services["clickhouse"]["image"] == "clickhouse/clickhouse-server@sha256:8a790dd3468db22b1d4e7b18a176f378ff5ff6053b9c48dd4ea1fa71a24c5ba6"
    assert services["redis"]["image"] == "redis@sha256:17e1d479466f88e2d8fe48f21f44aba1572bf3bbc207be16b09870072b83b005"
    assert "sha256:4cf4831a2bbcf13ddca09c1cbcc9faff716dd3c4247e0babc32864b8ee8e0034" in services["minio"]["image"]
    assert services["langfuse-web"]["ports"] == ["127.0.0.1:3300:3000"]
    assert all("ports" not in services[name] for name in services if name != "langfuse-web")


def test_langfuse_stack_has_healthy_dependencies_and_headless_project_bootstrap():
    services = _compose()["services"]
    for service_name in ("langfuse-web", "langfuse-worker"):
        assert set(services[service_name]["depends_on"]) == {"postgres", "clickhouse", "redis", "minio"}
        assert all(item["condition"] == "service_healthy" for item in services[service_name]["depends_on"].values())
    env = services["langfuse-web"]["environment"]
    assert env["LANGFUSE_MIGRATION_V4_WRITE_MODE"] == "events_only"
    assert env["LANGFUSE_INIT_PROJECT_ID"] == "agent-finops-poc"
    assert env["LANGFUSE_INIT_PROJECT_PUBLIC_KEY"] == "${FINOPS_LANGFUSE_PUBLIC_KEY}"
    assert env["LANGFUSE_INIT_PROJECT_SECRET_KEY"] == "${FINOPS_LANGFUSE_SECRET_KEY}"
    assert env["NEXTAUTH_URL"] == "http://localhost:3300"


def test_finops_secrets_are_ignored_and_smoke_tool_is_bounded():
    assert ".env.finops" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    smoke = (ROOT / "scripts" / "smoke-langfuse-finops.py").read_text(encoding="utf-8")
    assert "timeout=5" in smoke
    assert "time.monotonic" in smoke
    assert "input" in smoke and "output" in smoke
    assert "costDetails" in smoke
