# ZenML Deployers Package

## Purpose
The deployers package defines how ZenML turns pipeline snapshots into long-running HTTP services and keeps track of their lifecycle. Deployers sit in a ZenML stack, provision external infrastructure, register deployments in the ZenML store, and expose helpers to interact with those deployments.

## Key Modules
- `base_deployer.py`: Core abstract base defining the deployer contract. Handles provisioning/deprovisioning orchestration, snapshot validation, analytics tracking, and timeout/auth key management. Subclasses implement the `do_*` hooks for concrete platforms.
- `containerized_deployer.py`: Adds shared logic for deployers that rely on container images. Establishes image lookup rules, dependency requirements, and Docker build configuration generation.
- `exceptions.py`: Canonical error hierarchy used across deployers.
- `utils.py`: Convenience helpers to read deployment schemas, build invocation payloads, and call running deployments over HTTP.

## Concrete Implementation
- `docker/`
  - `docker_deployer.py`: Implements a local container-based deployer using Docker. Manages container lifecycle, port allocation, volume/UID wiring, log streaming, and exposes flavor/config/settings classes. Requires an image builder in the stack and relies on the reusable containerized base.

## Embedded Serving Runtime
- `server/`
  - `app.py`: FastAPI application that loads a `PipelineDeploymentService`, wires `/invoke`, `/health`, `/info`, and `/metrics` endpoints, and enforces optional bearer auth.
  - `entrypoint_configuration.py`: Entry-point wiring used when the deployment container boots. Validates CLI options, pulls snapshot metadata, and launches `uvicorn` with the right environment.
  - `models.py`: Pydantic models (request/response/service metadata) generated dynamically to mirror the deployed pipeline schema.
  - `runtime.py`: Request-scoped context/state helpers for serving invocations (in-memory outputs, artifact skipping, parameter injection).
  - `service.py`: Execution engine that loads the snapshot, spins up a shared local orchestrator, tracks runs/metrics, and glues runtime state to ZenML stores and hooks.

## Extending Deployers
To add a new deployer flavor, implement a subclass of `BaseDeployer` (or `ContainerizedDeployer` when running containers), provide matching config/settings classes, and a flavor class exposing metadata. Reuse the server package if the platform hosts the bundled FastAPI app, or supply an alternative runtime if required.
