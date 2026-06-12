## 1. POC Configuration Tests

- [x] 1.1 Add tests that validate Docker Compose runs Kong in DB-less mode
- [x] 1.2 Add tests that validate Kong routes preserve `/v1`, `/health`, and `/readiness`
- [x] 1.3 Add tests that validate request correlation and local rate limiting plugins are configured

## 2. Kong POC Files

- [x] 2.1 Add Kong declarative config under `kong/kong.yml`
- [x] 2.2 Add local `docker-compose.kong.yml`
- [x] 2.3 Keep the POC isolated from existing Kubernetes production manifests

## 3. Documentation And Verification

- [x] 3.1 Update README with Kong POC run and verification steps
- [x] 3.2 Run the full test suite and strict OpenSpec validation
- [x] 3.3 Commit the Phase 2 POC separately
