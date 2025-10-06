# ZenML Deployers Agents Guide

This document covers the modules under `zenml.deployers` and their subpackages. It is meant to help agents reason about how deployments are managed, how containerized deployers work, and how the serving runtime exposes pipelines.

## Directory Layout
- `base_deployer.py`: shared abstractions and workflow glue for all deployers.
- `containerized_deployer.py`: container-oriented mixins on top of the base deployer.
- `docker/`: concrete Docker implementation of a containerized deployer.
- `exceptions.py`: deployer-specific exception hierarchy.
- `server/`: FastAPI application and runtime used to serve deployed pipelines.
- `utils.py`: helper functions for interacting with deployments from code.

## Base Deployer Stack
`BaseDeployer` in `base_deployer.py` defines the public contract for ZenML deployers. Key pieces:
- Settings and config: `BaseDeployerSettings` (runtime knobs such as `auth_key`, `generate_auth_key`, `lcm_timeout`) and `BaseDeployerConfig` (stack/component configuration).
- Lifecycle operations: `provision_deployment`, `refresh_deployment`, `get_or_create_deployment`, `delete_deployment`, and `get_deployment_logs` orchestrate broader flows while delegating concrete work to `do_*` abstract methods implemented by flavors.
- Validation helpers: `_check_deployment_inputs_outputs`, `_check_deployment_deployer`, `_check_deployment_snapshot`, `_check_snapshot_already_deployed` guard against inconsistent state when provisioning or updating deployments.
- Auth support: `_generate_auth_key` produces secure random keys when `generate_auth_key` is enabled.
- Polling and analytics: `_poll_deployment` waits for state transitions, `_get_deployment_analytics_metadata` enriches telemetry, and `track_handler` instrumentation wraps provisioning/deprovisioning.
- Abstract hooks every subclass must implement (`do_provision_deployment`, `do_get_deployment_state`, `do_get_deployment_state_logs`, `do_deprovision_deployment`, and optionally `do_refresh_deployment`), as well as snapshot-based configuration overrides (`get_settings`, `get_docker_builds`, etc.).
- Flavor integration: `BaseDeployerFlavor` ties the deployer into the ZenML stack/registry system by advertising `StackComponentType.DEPLOYER` and returning the implementation class.

### Provisioning Flow (Happy Path)
1. Resolve or create a `DeploymentResponse` via the ZenML store, validating ownership and pipeline snapshot compatibility.
2. Compute environment variables (including active stack/project overrides) and gather secrets via `get_config_environment_vars`.
3. Call `do_provision_deployment` implemented by the concrete deployer.
4. Update persisted deployment state, emit analytics, and optionally poll until the deployment reaches `DeploymentStatus.RUNNING`.

Subclasses should surface meaningful `DeploymentOperationalState` updates so the base class can inform the user if provisioning stalls or errors.

## Containerized Deployers
`ContainerizedDeployer` extends `BaseDeployer` with helpers for Docker/OCI-based runtimes:
- `CONTAINER_REQUIREMENTS` lists extra Python packages baked into deployer images.
- `get_image` extracts the deployer image from the snapshot build (`DEPLOYER_DOCKER_IMAGE_KEY`).
- `requirements` augments pip dependencies, adding `zenml[local]==<version>` when connected to a SQL store so the container can access the database.
- `get_docker_builds` advertises the required build configuration so the orchestration layer produces the image ahead of deployment.

## Docker Deployer
The `docker` package contains the local Docker flavor.

`DockerDeployer` implements container lifecycle management:
- Depends on `uvicorn` and `fastapi` in `CONTAINER_REQUIREMENTS` and enforces an image builder in the stack via `StackValidator`.
- Lazily initializes a `DockerClient` from the environment.
- Maps `DeploymentResponse` metadata to Docker state through
  `DockerDeploymentMetadata`.
