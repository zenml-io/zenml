---
description: Executing sandbox sessions with Modal.
---

# Modal Sandbox

[Modal](https://modal.com/) is a cloud execution platform designed for running code with fast startup and flexible resource controls. ZenML's Modal sandbox flavor lets you run isolated sessions on Modal directly from your stack.

### When to use it

Use the Modal sandbox if you need:

* Rich cloud sandbox capabilities (networking, tunnels, snapshots, streaming).
* GPU-enabled sandbox sessions.
* Fine-grained network policy controls for outbound access.

### How to deploy it

To use the Modal sandbox flavor:

* Install the Modal integration:

  ```shell
  zenml integration install modal
  ```

* Authenticate with Modal if needed:

  ```shell
  modal setup
  ```

* Register a sandbox component:

  ```shell
  zenml sandbox register <NAME> --flavor=modal
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox <NAME>
  ```

### Configuration highlights

`ModalSandboxConfig` defaults:

* `app_name`: `zenml-sandbox`
* `default_image`: `python:3.11-slim`
* `default_timeout_seconds`: `300`
* `default_cpu`: `1.0`
* `default_memory_mb`: `2048`

Additional config fields:

* `cpu_cost_per_core_second_usd`: Optional CPU cost metadata for estimates.
* `memory_cost_per_gib_second_usd`: Optional memory cost metadata for estimates.

`ModalSandboxSettings` fields:

* `block_network`: Whether outbound network access should be blocked.
* `cidr_allowlist`: Optional CIDR ranges that remain reachable.
* `verbose`: Whether to show verbose Modal execution output.

### Capabilities

Modal currently advertises the following sandbox capabilities:

* `filesystem`
* `networking`
* `tunnels`
* `snapshots`
* `streaming`
* `persistent`
* `gpu`

It does not currently advertise `exec_cancel`.

### Modal-specific notes

* Network policy can be set with the base `network_policy` setting. If it is not set, Modal-specific `block_network` and `cidr_allowlist` settings are used to construct the policy.
* Session metadata includes a pricing reference: [https://modal.com/pricing](https://modal.com/pricing).
