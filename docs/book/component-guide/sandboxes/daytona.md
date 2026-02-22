---
description: Executing sandbox sessions with Daytona.
---

# Daytona Sandbox

[Daytona](https://www.daytona.io/) provides remote sandbox environments for running code in isolated workspaces. The ZenML Daytona sandbox flavor integrates those workspaces as a stack component.

### When to use it

Use the Daytona sandbox if you want:

* Remote sandbox sessions with persistent state.
* Filesystem access and streaming command output.
* Control over lifecycle behavior such as ephemeral sessions, auto-stop, and auto-delete intervals.

### How to deploy it

To use the Daytona sandbox flavor:

* Install the Daytona integration:

  ```shell
  zenml integration install daytona
  ```

* Register a sandbox component:

  ```shell
  zenml sandbox register <NAME> --flavor=daytona
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox <NAME>
  ```

### Configuration highlights

`DaytonaSandboxConfig` defaults:

* `default_image`: `python:3.12`
* `default_cpu`: `2`
* `default_memory_gb`: `4`
* `default_disk_gb`: `8`

`DaytonaSandboxSettings` fields:

* `api_url`: Custom Daytona API endpoint.
* `target`: Target runtime where the sandbox should run.
* `ephemeral`: Whether sessions are automatically deleted when stopped.
* `auto_stop_interval_minutes`: Inactivity threshold before Daytona auto-stops a session.
* `auto_delete_interval_minutes`: Delay before auto-deleting a stopped session.

### Capabilities

Daytona currently advertises the following sandbox capabilities:

* `filesystem`
* `streaming`
* `persistent`

It does not currently advertise `networking`, `tunnels`, `snapshots`, `gpu`, or `exec_cancel` capabilities.

### Daytona-specific notes

* The `gpu` setting currently expects a numeric GPU count. Non-numeric values are ignored by the provider.
* Network policy settings (`block_network` and CIDR allowlist) can be passed through to Daytona session creation.
* Cost metadata is currently marked as unavailable in the Daytona provider implementation.
