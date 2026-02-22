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

### Quick example

Here is a minimal pipeline step that runs a command inside a sandbox session:

```python
from zenml import step, pipeline
from zenml.steps import get_step_context

@step(sandbox=True)
def sandboxed_step() -> str:
    ctx = get_step_context()
    if ctx.sandbox is None:
        raise RuntimeError("No sandbox in the active stack.")

    with ctx.sandbox.session(
        image="python:3.12",
        timeout_seconds=300,
    ) as sb:
        result = sb.exec_run(
            ["python", "-c", "print('hello from sandbox')"]
        )
    return result.stdout.strip()

@pipeline
def my_pipeline():
    sandboxed_step()
```

Key things to notice:

1. **`sandbox=True`** on the step decorator tells ZenML this step will use the sandbox component.
2. **`get_step_context().sandbox`** gives you the sandbox component attached to the active stack.
3. **`session()`** is a context manager — all commands run inside `with ... as sb:` share the same sandbox session (same container, same filesystem state).

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

{% hint style="warning" %}
Calling a method for an unsupported capability (e.g. `write_file` on a Monty session) raises a clear `NotImplementedError` with a message like *"MontySandboxSession does not support filesystem operations."* You can check capabilities ahead of time with `ctx.sandbox.has_capability(SandboxCapability.FILESYSTEM)`.
{% endhint %}

### Provider differences at a glance

Beyond the capability table, the providers differ in several important behavioral ways:

| Behavior | Daytona | Modal | Monty |
| --- | --- | --- | --- |
| **Execution model** | Remote container | Remote container | Local in-process |
| **`image` setting** | Creates a remote workspace with that image | Builds a Modal sandbox image | Accepted for API consistency but not used for provisioning |
| **GPU support** | Numeric count only (strings like `"A10G"` are ignored) | Full GPU type support | Not applicable |
| **Network policy** | Forwarded at creation time, but not advertised as a capability | Full networking capability with CIDR allowlists | Not applicable |
| **Cost metadata** | Not available (`"not available in daytona provider v1"`) | Estimated when pricing rates are configured | Always `0.0` (local execution) |
| **Code interpreter** | Supported (persistent Python REPL) | Supported, but requires direct router connectivity | Supported, but incompatible with `external_functions` |

### Common session patterns

#### One session, many commands

A single `session()` call keeps state between commands. This means installed packages, written files, and environment variables persist across `exec_run` calls — exactly like running multiple commands in the same terminal:

```python
with ctx.sandbox.session(image="python:3.12") as sb:
    sb.exec_run(["pip", "install", "pandas"])
    sb.exec_run(["python", "-c", "import pandas; print(pandas.__version__)"])
```

#### Error handling with `check=True`

By default, `exec_run` returns the result even on non-zero exit codes. Pass `check=True` to raise a `SandboxExecError` on failure:

```python
from zenml.sandboxes import SandboxExecError

try:
    sb.exec_run(["python", "-c", "import sys; sys.exit(1)"], check=True)
except SandboxExecError as e:
    print(f"Exit code: {e.result.exit_code}")
    print(f"Stderr: {e.result.stderr}")
```

The error message includes the exit code and the last ~10 lines of stderr for quick debugging.

#### Streaming output

For long-running commands where you want real-time output, use `exec_streaming` (requires the `streaming` capability):

```python
process = sb.exec_streaming(
    ["python", "-u", "-c", "for i in range(5): print(f'step {i}')"]
)
for line in process.stdout_iter():
    print(line, end="")
exit_code = process.wait(timeout_seconds=60)
```

{% hint style="info" %}
When collecting streamed output, avoid reading until EOF if you know the expected line count. Read a bounded number of lines to prevent hanging on processes that don't close their output streams immediately.
{% endhint %}

#### Persistent code interpreter

The `code_interpreter()` method provides a persistent Python REPL where state carries over between calls:

```python
with sb.code_interpreter() as interp:
    interp.run("counter = 0")
    interp.run("counter += 1")
    result = interp.run("counter")
    print(result.output)  # 2
```

#### File operations

Providers with the `filesystem` capability (Daytona, Modal) support reading and writing files inside the sandbox:

```python
sb.write_file("/tmp/data.txt", "hello world")
content = sb.read_file("/tmp/data.txt").decode("utf-8")
```

### Configuration precedence

Sandbox settings follow a three-tier precedence rule — the most specific value wins:

1. **Session call arguments** (highest priority): values passed directly to `ctx.sandbox.session(image=..., cpu=..., ...)`
2. **Step-level settings**: values in `@step(settings={"sandbox.<flavor>": ...})`
3. **Component config defaults** (lowest priority): values set when you registered the sandbox with `zenml sandbox register ...`

This lets you set sensible defaults on the component, override per-step where needed, and still make one-off adjustments at session creation time.

**Environment variable merge behavior:**
* Secret references (`secret_refs`) are resolved first from the ZenML secrets store
* Explicit `env` values then override any conflicting secret-resolved keys
* This means you can use secrets for production credentials while overriding specific vars for debugging

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

### Automatic metadata: `sandbox_info`

When a step uses a sandbox, ZenML automatically emits structured metadata under the `sandbox_info` key. You can inspect this in the dashboard or via the client. The metadata includes:

* `provider` — which sandbox flavor was used
* `session_count` — how many sessions the step opened
* `total_commands_executed` — aggregate command count across sessions
* `total_duration_seconds` — total time spent in sandbox sessions
* `capabilities` — list of capabilities the provider advertises
* `sessions` — per-session detail including duration, command count, and provider-specific extras (image, cost estimates, etc.)

Example shape:

```json
{
  "sandbox_info": {
    "provider": "modal",
    "session_count": 1,
    "total_commands_executed": 3,
    "total_duration_seconds": 12.5,
    "total_estimated_cost_usd": 0.0042,
    "capabilities": ["filesystem", "gpu", "networking", "persistent", "snapshots", "streaming", "tunnels"],
    "sessions": [
      {
        "session_id": "sb-abc123",
        "provider": "modal",
        "duration_seconds": 12.5,
        "commands_executed": 3,
        "estimated_cost_usd": 0.0042,
        "extra": {"image": "python:3.11-slim"}
      }
    ]
  }
}
```

{% hint style="warning" %}
If a step declares `sandbox=True` but never calls `sandbox.session()`, ZenML logs a warning: *"Step 'my_step' declared sandbox=True but no sandbox sessions were created. Did you forget to call sandbox.session()?"* This helps catch configuration mistakes early.
{% endhint %}
