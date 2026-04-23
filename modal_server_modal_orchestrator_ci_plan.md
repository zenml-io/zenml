# Investigation: Modal-backed Server + Orchestrator CI Lane

## Summary

The current `docker-server-docker-orchestrator-mysql` CI lane tests a remote ZenML server over REST, a MySQL store, and containerized remote-style pipeline execution. A true `modal-server-modal-orchestrator-mysql` replacement is feasible, but not as a simple config swap: ZenML's Modal orchestrator requires a remote artifact store, remote container registry, image builder, and ZenML-visible registry credentials.

The pragmatic plan is phased: first wire and validate `modal-server-mysql`, then add a targeted Modal-orchestrator smoke lane with remote artifact/registry credentials, and only replace the broad Docker lane after runtime and stability are proven.

## Symptoms / Goal

- Current fast CI has a dedicated job for `docker-server-docker-orchestrator-mysql`.
- The desired coverage is not Docker daemon semantics specifically.
- The desired coverage is:
  - ZenML client connects to a remote ZenML server over REST.
  - Server uses MySQL.
  - Pipeline execution uses a remote/containerized orchestrator.
- Desired runtime target is sub-5 minutes using Modal-backed infrastructure where practical.

## Investigation Log

### Current CI Flow

**Hypothesis:** `docker-server-docker-orchestrator-mysql` is a standard sharded integration workflow with harness-managed provisioning.

**Findings:** Confirmed.

**Evidence:**
- `.github/workflows/ci-fast.yml:113-127` defines `ubuntu-latest-docker-integration-test`, Python 3.11, with `test_environment: [docker-server-docker-orchestrator-mysql]`.
- `.github/workflows/integration-test-fast.yml:288-294` runs the integration suite as 6 Ubuntu shards via `bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT} 6 ${{ matrix.shard }}`.
- `scripts/test-coverage-xml.sh:50-70` provisions the environment once, runs pytest with `--environment $TEST_ENVIRONMENT --no-provision`, then cleans up.

**Conclusion:** The current lane is not offload-based. It is GitHub Actions sharding with one provisioned environment per shard/job.

### Current Environment Composition

**Hypothesis:** The current environment is server+MySQL plus mandatory Docker orchestrator.

**Findings:** Confirmed.

**Evidence:**
- `tests/harness/cfg/environments.yaml:135-145` defines `docker-server-docker-orchestrator-mysql` with `deployment: docker-server-mysql` and `mandatory_requirements: [docker-local]`.
- `tests/harness/cfg/deployments.yaml:100-106` defines `docker-server-mysql` as `server: docker`, `database: mysql`, with `server: true` capability.
- `tests/harness/cfg/requirements.yaml:123-131` defines `docker-local` as a `local_docker` orchestrator with `containerized: true` and `synchronized: true`.

**Conclusion:** The current lane tests REST/server/MySQL plus the `local_docker` orchestrator. It does not configure a remote artifact store, remote registry, or explicit image builder.

### Existing Modal Server Harness

**Hypothesis:** A Modal-hosted ZenML server + MySQL deployment already exists and only needs YAML wiring.

**Findings:** Confirmed.

**Evidence:**
- `tests/harness/deployment/server_modal_mysql.py:91-151` builds a Modal image, creates a Modal app/sandbox, exposes port `8080` via `encrypted_ports`, and stores the tunnel URL.
- `tests/harness/deployment/server_modal_mysql.py:189-206` returns a `DeploymentStoreConfig` using the Modal tunnel URL and default credentials.
- `tests/harness/deployment/server_modal_mysql.py:210-212` registers the deployment for `(ServerType.MODAL, DatabaseType.MYSQL)`.
- `tests/harness/deployment/_modal_runtime.py:79-90` requires `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` for CI Modal auth.
- `tests/harness/deployment/_modal_runtime.py:119-148` builds a Modal image from a DB base image, adds the repo source, installs `zenml[server]`, and sets server env vars.
- `tests/harness/cfg/deployments.yaml:96-124` currently has no `server: modal` deployment entry.

**Conclusion:** `modal-server-mysql` is mostly implemented in Python but not exposed through harness config.

### True Modal Orchestrator Requirements

**Hypothesis:** A true `modal-server-modal-orchestrator-mysql` environment can reuse local artifact store and local/default registry.

**Findings:** Eliminated. The Modal orchestrator explicitly rejects local artifact stores and local container registries and requires image-builder + container-registry components.

**Evidence:**
- `src/zenml/integrations/modal/orchestrators/modal_orchestrator.py:80-89` rejects local artifact stores.
- `src/zenml/integrations/modal/orchestrators/modal_orchestrator.py:91-101` rejects local container registries.
- `src/zenml/integrations/modal/orchestrators/modal_orchestrator.py:105-109` requires `CONTAINER_REGISTRY` and `IMAGE_BUILDER` stack components.
- `src/zenml/integrations/modal/orchestrators/modal_orchestrator.py:177-184` requires `stack.container_registry.credentials` and raises `RuntimeError` if missing.
- `tests/harness/model/requirements.py:255-264` provisions stack components from YAML, but the investigated provisioning path does not create ZenML secrets/service connectors needed by `authentication_secret`-backed registry credentials.

**Conclusion:** A pure Modal-orchestrator lane needs additional cloud/test infrastructure: remote artifact store, remote registry, image builder, and ZenML-managed registry credentials.

## Root Cause / Key Constraint

The blocker is not whether Modal can run containers. The blocker is ZenML stack validity for the Modal orchestrator.

The current Docker lane works with simple local components:
- default/local artifact store,
- no container registry requirement in environment YAML,
- `local_docker` orchestrator as mandatory requirement.

The Modal orchestrator is stricter because steps run outside the machine/server context. It must be able to:
- write/read artifacts from a remote artifact store,
- pull step images from a remote container registry,
- build/push images through an image builder + registry,
- provide registry credentials to Modal as a Modal secret.

Those requirements are enforced in `modal_orchestrator.py:72-109` and `modal_orchestrator.py:177-184`.

## Recommended Plan

### Phase 0 — Do not silently replace Docker semantics with Modal semantics

Make the coverage change explicit in CI naming and docs. The desired new lane is not equivalent to Docker orchestrator coverage. It is REST + MySQL + Modal remote execution coverage.

### Phase 1 — Wire `modal-server-mysql` as a standalone environment

Purpose: validate the existing Modal-hosted ZenML server + MySQL harness without involving Modal orchestrator complexity.

Changes:
1. Add deployment in `tests/harness/cfg/deployments.yaml`:

```yaml
  - name: modal-server-mysql
    description: >-
      ZenML server and MySQL running together inside a Modal sandbox.
      The server is reachable from the test runner via a Modal TLS tunnel.
    server: modal
    database: mysql
    capabilities:
      server: true
```

2. Add environment in `tests/harness/cfg/environments.yaml`:

```yaml
  - name: modal-server-mysql
    description: >-
      Modal sandbox deployment with ZenML server and MySQL, using the default
      local orchestrator and local stack components.
    deployment: modal-server-mysql
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true
```

3. Ensure `tests/harness/deployment/__init__.py` imports `server_modal_mysql` and `server_modal_mariadb` so their registration side effects run.

4. Add `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` to the relevant workflow env and install Modal SDK for `contains(inputs.test_environment, 'modal')`.

Validation:
- Run a small server/API subset against `modal-server-mysql` first.
- This tests REST + MySQL on Modal without remote step execution.

### Phase 2 — Add targeted `modal-server-modal-orchestrator-mysql` smoke lane

Purpose: validate the full desired architecture with a small, deterministic suite before broad replacement.

Required harness/config additions:
1. `modal-orchestrator` requirement:

```yaml
  - name: modal-orchestrator
    integrations: [modal]
    stacks:
      - name: modal-orchestrator
        type: orchestrator
        flavor: modal
    capabilities:
      synchronized: true
```

2. Remote artifact store requirement, e.g. S3/GCS/Azure, with per-run path prefix to avoid state collisions.
3. Remote container registry requirement, e.g. DockerHub/GHCR/ECR/GCR.
4. Explicit image builder requirement.
5. Harness support for creating ZenML secrets/service connectors before component registration, because the container registry must expose credentials through `stack.container_registry.credentials`.

Example desired environment shape:

```yaml
  - name: modal-server-modal-orchestrator-mysql
    description: >-
      Modal-hosted ZenML server and MySQL with Modal orchestrator for remote
      step execution. Requires Modal credentials, remote artifact store,
      remote container registry, and registry credentials provisioned as ZenML
      secrets/connectors.
    deployment: modal-server-mysql
    mandatory_requirements:
      - modal-orchestrator
      - modal-remote-artifact-store
      - modal-container-registry
      - modal-image-builder
```

Workflow requirements:
- Modal credentials for server provisioning and Modal orchestrator execution.
- Artifact store credentials.
- Container registry credentials.
- Docker login if using local image builder to push images.
- Guard the job to internal PRs / trusted branches only.

Validation suite:
- One simple pipeline that runs through Modal orchestrator.
- Verify run metadata via the server REST API.
- Verify artifact read/write through remote artifact store.
- Verify MySQL-backed metadata persists.

### Phase 3 — Decide whether to replace broad Docker lane

Only after Phase 2 is stable:
- compare runtime,
- compare flake rate,
- compare Modal + registry + artifact-store cost,
- decide whether to replace `ubuntu-latest-docker-integration-test` or keep a small Docker smoke lane.

Recommended CI end state if Phase 2 proves stable:
- Broad fast lane: `modal-server-modal-orchestrator-mysql` subset/offload.
- Small Docker smoke lane: keep minimal `docker-server-docker-orchestrator-mysql` coverage for Docker-specific regressions.

## Shared Server vs Per-Sandbox / Per-Job

### Existing harness behavior

Current `scripts/test-coverage-xml.sh` provisions once per GitHub Actions shard/job, runs tests with `--no-provision`, then cleans up. That is evidenced at `scripts/test-coverage-xml.sh:50-70`.

`ServerModalMySQLTestDeployment` creates a unique Modal app name for each `up()` call (`server_modal_mysql.py:124-132`) and stores the tunnel URL in memory. There is no stable shared server mechanism today.

### Recommendation

For Phase 1 and Phase 2 smoke:
- use one Modal server per CI shard/job, matching existing harness behavior.
- This is the least invasive path and preserves isolation.

For sub-5 broad offload later:
- use a pre-provisioned shared server only after adding explicit test isolation:
  - per-run project namespace,
  - per-batch/user stack naming,
  - artifact path prefixes,
  - cleanup logic resilient to parallel batches.

Do not start with shared server across all offload sandboxes. It is faster in theory but has high shared-state risk.

## Risks

1. **True Modal orchestrator needs more infra than current Docker lane.**
   - Mitigation: Phase it behind a smoke lane and explicit secrets.

2. **Registry credentials must be visible to ZenML, not just Docker CLI.**
   - Mitigation: extend harness to create ZenML secrets/connectors before stack components.

3. **Remote artifact store collisions across parallel jobs.**
   - Mitigation: per-run unique artifact path prefix.

4. **Modal server cold image build can dominate runtime.**
   - Mitigation: Modal image caching; start with small smoke; measure before broad replacement.

5. **Shared server can cause cross-test pollution.**
   - Mitigation: start with per-job server; only share after explicit isolation work.

## Preventive Measures

- Keep CI environment names semantically honest: do not call Modal orchestrator coverage a Docker-orchestrator replacement without noting the coverage shift.
- Add validation tests for harness environments so missing `deployments.yaml` entries are caught before CI runtime.
- Document cloud-secret prerequisites for `modal-server-modal-orchestrator-mysql`.
- Keep a small Docker-orchestrator smoke job if Docker-specific behavior remains important.
