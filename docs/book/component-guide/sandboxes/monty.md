---
description: Executing lightweight local sandbox sessions with Monty.
---

# Monty Sandbox

The Monty sandbox flavor uses [pydantic-monty](https://github.com/pydantic/pydantic-ai/tree/main/pydantic_monty) to provide lightweight, in-process sandbox sessions. It is intended for local execution scenarios where low overhead matters.

### When to use it

Use the Monty sandbox if you want:

* Local-only sandbox behavior.
* Fast, lightweight sessions in the current execution environment.
* Snapshot and persistent-session capabilities without remote infrastructure.

### How to deploy it

To use the Monty sandbox flavor:

* Install the Monty integration:

  ```shell
  zenml integration install monty
  ```

* Register a sandbox component:

  ```shell
  zenml sandbox register <NAME> --flavor=monty
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox <NAME>
  ```

### Configuration highlights

`MontySandboxConfig` fields:

* `type_check` (default: `True`): Enables type checking in Monty execution.
* `raise_on_failure` (default: `True`): Raises execution errors automatically.

`MontySandboxSettings` fields:

* `external_functions`: Optional map of declared external functions.
* `type_check_stubs`: Optional type-checking stubs passed to the sandbox session.

### Capabilities

Monty currently advertises the following sandbox capabilities:

* `snapshots`
* `persistent`

It does not currently advertise `filesystem`, `networking`, `tunnels`, `streaming`, `gpu`, or `exec_cancel`.

### Monty-specific notes

* `MontySandboxConfig.is_remote` is `False` and `is_local` is `True`, so this flavor is local-only.
* Session metadata includes type-check and declared external-function details for traceability.
