# Shared Kong on GKE: ownership and operations

This repository owns the shared model ingress configuration, Kubernetes manifests,
configuration tests and release/rollback procedure. Application repositories own
their client configuration and integration tests. `ai-platform` owns cross-service
runtime orchestration and application-facing HTTPRoute definitions.

## Authoritative assets

- `k8s/kong-config.yaml`: DB-less configuration, upstream routes and plugins.
- `k8s/kong-deployment.yaml`: Kong workload, version, resources and probes.
- `k8s/kong-service.yaml`: internal service contract.
- `tests/test_kong_gke_manifests.py`: GKE resource contract tests.
- `kong/kong.yml` and `docker-compose.kong.yml`: local development overlay.

The three GKE files were moved unchanged from ai-market-studio. The public consumer
contract remains `http://ai-gateway-kong.ai-gateway.svc.cluster.local/v1`, forwarding
to `http://ai-gateway.ai-gateway.svc.cluster.local`. All resources remain in namespace
`ai-gateway`; no resource recreation, DNS change or policy change is needed.

Application rollout must not apply these files. Gateway's `cloudbuild.yaml` builds
and pushes the Python service image only; it does not deploy Kong. Kong releases
are an independent, explicit operator action using a reviewed Git revision.

## Environment differences retained

| Setting | Local | GKE |
|---|---|---|
| Image | `kong:3` | `kong:3.7` |
| Upstream | Compose service, port 4000 | Kubernetes Service DNS, port 80 |
| Routes | `/v1`, `/health`, `/readiness`, preserve path | Same |
| Rate limit | 120/min, local | 120/min + 5000/hour, local |
| Transport settings | Explicit connect/read/write 5000/60000/60000ms; retries 2 | Unspecified in declarative config |
| Admin listener | Local port 8001 | Off |

These are existing differences, not policy decisions introduced by the move. Do
not mechanically copy the local overlay over GKE. Pinning immutable versions and
reconciling transport/quota policy require a separate reviewed change.
AI Proxy and Prompt Guard Compose experiments remain isolated and are not part of
the shared GKE release.

## Release (run only when deployment is requested)

Use the intended GKE context and a reviewed repository revision. Record the context,
Git revision, current Kong image and previous known-good revision before changing it.
Keep namespace/resource names stable. From this repository:

```powershell
kubectl config current-context
git rev-parse HEAD
kubectl get deployment ai-gateway-kong -n ai-gateway -o wide
kubectl apply -f k8s/kong-config.yaml
kubectl apply -f k8s/kong-deployment.yaml
kubectl apply -f k8s/kong-service.yaml
kubectl rollout restart deployment/ai-gateway-kong -n ai-gateway
kubectl rollout status deployment/ai-gateway-kong -n ai-gateway --timeout=300s
```

Check each exit code and stop on failure. Explicit restart includes ConfigMap-only
changes in the rollout; do not treat applying a ConfigMap as proof of effective
runtime configuration. Inspect workload events/logs and verify the deployed
ConfigMap against the selected revision. This POC's single replica does not promise
zero-downtime rollout.

For a no-model-cost smoke check, port-forward in a separate terminal:

```powershell
kubectl port-forward -n ai-gateway service/ai-gateway-kong 18000:80
curl.exe --fail http://localhost:18000/health
curl.exe --fail http://localhost:18000/readiness
```

Verify `/v1/models` using the configured Gateway service token when authentication
is enabled. Check X-Request-ID correlation and an application-side contract call.
Health checks alone do not prove the quota or a changed route is effective; verify
the changed behavior with bounded synthetic requests appropriate to that change.
Provider-backed chat/embedding checks are a separate explicit smoke test.

## Rollback

Use the recorded known-good Git revision of **all three** Kong manifests from this
repository, from a clean checkout or detached worktree. Apply those files, restart
Kong, wait for rollout and rerun the same contract checks. A Deployment rollback
alone is insufficient to restore the mutable ConfigMap. Do not roll back an entire
`k8s/` directory or delete shared resources.

For the first ownership migration, retain the original three-file snapshot and
source revision (`ai-market-studio` 53acf54) until the first Gateway-owned release
has a recorded known-good revision. The ownership move itself does not update GKE.

Changing one application's URL to bypass Kong is an application contingency,
not a shared ingress rollback; it also bypasses Kong policies.

## Responsibility and runtime startup

- Gateway maintainer: Kong changes, validation, release, rollback and initial
  diagnosis of ingress route/rate-limit/availability failures. Assign the actual
  person/team in the project's operating agreement; this document does not invent one.
- Application maintainer: client headers, base URL, application failures and consumer tests.
- Platform operator: coordinated startup of existing shared workloads using
  `ai-platform/scripts/start-shared-runtime.ps1`; no application deployment should
  implicitly scale Kong. This script is not a release pipeline.

Start shared workloads before Requirement Tool's application startup. Its
`start-gcp-runtime.ps1` checks shared endpoints but changes only Redis, ai-tool and
Celery. Shared resources use their owning service manifests; previous application
startup overrides of RAG resources have been removed.
