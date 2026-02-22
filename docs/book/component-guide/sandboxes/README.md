---
description: Running isolated execution sessions as a stack component.
icon: square-terminal
---

# Sandboxes

A sandbox is an optional ZenML stack component that gives pipeline steps an isolated session for running commands or code. Sandboxes are useful when a step needs controlled execution that is separate from the step process itself.

{% hint style="info" %}
**Comparison to other execution components:** The [orchestrator](https://docs.zenml.io/stacks/orchestrators/) schedules and runs pipeline steps. [Step operators](https://docs.zenml.io/stacks/step-operators/) offload entire steps to specialized runtimes. A sandbox gives a step an isolated session that it can control programmatically at runtime.
{% endhint %}

### When to use it

Use a sandbox when you need:

* Isolated command execution with controlled resources.
* Persistent sessions that keep state across multiple commands.
* Provider-specific capabilities like networking, tunnels, snapshots, and GPUs.

### Sandbox Flavors

Sandbox implementations are provided by the following integrations:

| Sandbox | Flavor | Integration | Notes |
| --- | --- | --- | --- |
| [Daytona](daytona.md) | `daytona` | `daytona` | Remote cloud sandboxes with filesystem + streaming output + persistent sessions |
| [Modal](modal.md) | `modal` | `modal` | Rich cloud sandbox feature set including networking, tunnels, and GPU |
| [Monty](monty.md) | `monty` | `monty` | Lightweight local in-process sandbox with snapshots + persistent sessions |

If you would like to see the available flavors of sandboxes, you can use the command:

```shell
zenml sandbox flavor list
```

### How to register and attach a sandbox

```shell
zenml sandbox register <SANDBOX_NAME> --flavor=<daytona|modal|monty>
zenml stack update <STACK_NAME> --sandbox <SANDBOX_NAME>
```

For a brand-new stack, you can register all required components at once:

```shell
zenml stack register <STACK_NAME> \
    -a <ARTIFACT_STORE> \
    -o <ORCHESTRATOR> \
    --sandbox <SANDBOX_NAME>
```

### Capability comparison

Each sandbox provider advertises a capability set through the `SandboxCapability` contract in `BaseSandbox`. The current integration capabilities are:

| Capability | Daytona | Modal | Monty |
| --- | --- | --- | --- |
| `filesystem` | ✅ | ✅ | ❌ |
| `networking` | ❌ | ✅ | ❌ |
| `tunnels` | ❌ | ✅ | ❌ |
| `snapshots` | ❌ | ✅ | ✅ |
| `streaming` | ✅ | ✅ | ❌ |
| `persistent` | ✅ | ✅ | ✅ |
| `gpu` | ❌ | ✅ | ❌ |
| `exec_cancel` | ❌ | ❌ | ❌ |

### Common sandbox settings

All sandbox flavors inherit these base settings:

| Setting | Purpose |
| --- | --- |
| `timeout_seconds` | Maximum runtime per session or execution |
| `image` | Base image used for session execution (provider-dependent) |
| `cpu` | Requested CPU resources |
| `memory_mb` | Requested memory in MB |
| `gpu` | Requested GPU resources |
| `env` | Environment variables for the session |
| `secret_refs` | Secret references to resolve into environment variables |
| `network_policy` | Network access policy (`block_network` + CIDR allowlist) |
| `tags` | Metadata labels attached to sessions |

Provider-specific pages describe additional settings and behavior for each flavor.
