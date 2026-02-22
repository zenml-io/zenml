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
  zenml sandbox register modal-sb --flavor=modal
  ```

* Optionally, configure cost estimation rates:

  ```shell
  zenml sandbox update modal-sb \
      --cpu_cost_per_core_second_usd=0.00001 \
      --memory_cost_per_gib_second_usd=0.000001
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox modal-sb
  ```

### Realistic pipeline example

This example demonstrates Modal sandbox features including command execution, streaming, file I/O, and the important interpreter-with-fallback pattern:

```python
from zenml import step, pipeline
from zenml.sandboxes import SandboxExecError
from zenml.steps import get_step_context

@step(sandbox=True)
def modal_step() -> str:
    ctx = get_step_context()
    if ctx.sandbox is None:
        raise RuntimeError("No sandbox in the active stack.")

    with ctx.sandbox.session(
        image="python:3.11-slim",
        timeout_seconds=600,
        env={"MY_VAR": "hello"},
    ) as sb:
        # Run a command
        result = sb.exec_run(
            ["python", "-c", "print('hello from Modal sandbox')"]
        )

        # check=True raises on non-zero exit
        try:
            sb.exec_run(
                ["python", "-c", "import sys; sys.exit(3)"],
                check=True,
            )
        except SandboxExecError as e:
            print(f"Caught error: exit code {e.result.exit_code}")

        # Streaming — read lines as they arrive
        process = sb.exec_streaming(
            ["python", "-u", "-c",
             "for i in range(3): print(f'step {i}')"]
        )
        for line in process.stdout_iter():
            print(line, end="")
        process.wait(timeout_seconds=30)

        # File I/O
        sb.write_file("/tmp/example.txt", "modal sandbox content")
        content = sb.read_file("/tmp/example.txt").decode("utf-8")

        # Interpreter with fallback (see "Gotchas" below)
        try:
            with sb.code_interpreter() as interp:
                interp.run("counter = 0")
                interp.run("counter += 1")
                result = interp.run("output = counter")
                print(f"Interpreter result: {result.output}")
        except RuntimeError as e:
            if "direct command router connection" not in str(e):
                raise
            # Fallback: use run_code when interpreter is unavailable
            fallback = sb.run_code("print(42)")
            print(f"Fallback result: {fallback.stdout.strip()}")

    return content

@pipeline
def my_modal_pipeline():
    modal_step()
```

{% hint style="info" %}
The interpreter fallback pattern above is important. In some network environments, Modal's direct command router may not be reachable. When this happens, `code_interpreter()` raises a `RuntimeError`. The recommended pattern is to catch this and fall back to `run_code()`, which works through a different communication path.
{% endhint %}

### Configuration

#### Component config defaults (`ModalSandboxConfig`)

These are set when you register the sandbox and serve as the lowest-priority defaults:

| Field | Default | Description |
| --- | --- | --- |
| `app_name` | `zenml-sandbox` | Modal app name used for sandbox runs. All sessions share this app |
| `default_image` | `python:3.11-slim` | Base image. Passed through `build_modal_image()` which constructs a Modal-compatible image |
| `default_timeout_seconds` | `300` | Default session timeout (5 minutes) |
| `default_cpu` | `1.0` | CPU cores per session |
| `default_memory_mb` | `2048` | Memory per session (2 GB) |
| `cpu_cost_per_core_second_usd` | `None` | CPU pricing rate for cost estimates. Set to enable cost metadata |
| `memory_cost_per_gib_second_usd` | `None` | Memory pricing rate for cost estimates |

#### Step-level settings (`ModalSandboxSettings`)

These override component defaults per-step:

| Field | Default | Description |
| --- | --- | --- |
| `block_network` | `None` | Block all outbound network access |
| `cidr_allowlist` | `None` | CIDR ranges that remain reachable when network is blocked |
| `verbose` | `None` | Show verbose Modal execution output (enables `modal.enable_output()`) |

Plus all the common settings inherited from `BaseSandboxSettings` (`timeout_seconds`, `image`, `cpu`, `memory_mb`, `gpu`, `env`, `secret_refs`, `network_policy`, `tags`, `forward_output_to_step_logs`).

### Configuration precedence

Settings are resolved in this order (first match wins):

1. **Session call arguments**: `ctx.sandbox.session(image="python:3.12", cpu=4, ...)`
2. **Step settings**: `@step(settings={"sandbox.modal": ModalSandboxSettings(verbose=True)})`
3. **Component config defaults**: values from `zenml sandbox register ...`

### Network policy precedence (Modal-specific)

Modal has its own three-tier precedence for network policies:

1. **Explicit `network_policy`** passed to `session(network_policy=...)`
2. **Step-level `network_policy`** in `BaseSandboxSettings`
3. **Modal-specific settings** — if neither of the above is set, the policy is constructed from `ModalSandboxSettings.block_network` and `ModalSandboxSettings.cidr_allowlist`

When the resolved policy is applied:
* `block_network` is always forwarded to Modal
* `cidr_allowlist` is only included if it has a non-None value

### Capabilities

Modal currently advertises the following sandbox capabilities:

* `filesystem` — read/write files inside the sandbox
* `networking` — network access controls and outbound connectivity
* `tunnels` — open tunnels to sandbox ports for external access
* `snapshots` — capture sandbox state
* `streaming` — real-time stdout/stderr via `exec_streaming`
* `persistent` — sessions retain state across commands
* `gpu` — GPU-enabled sandbox sessions

### Cost estimation

Modal sandbox sessions can include cost estimates in their metadata if you configure pricing rates:

```shell
zenml sandbox update modal-sb \
    --cpu_cost_per_core_second_usd=0.00001 \
    --memory_cost_per_gib_second_usd=0.000001
```

Cost is estimated as: `(cpu_cores × cpu_rate × seconds) + (memory_gib × memory_rate × seconds)`.

If either the pricing rates or the resource values are missing, the metadata will include an `estimated_cost_reason` field explaining why the estimate could not be computed (e.g. `"missing resource values or pricing rates"`). See [Modal's pricing page](https://modal.com/pricing) for current rates.

### Gotchas and caveats

{% hint style="warning" %}
**Interpreter requires direct router connectivity.** The `code_interpreter()` method relies on Modal's direct command router. If DNS resolution for the router fails (e.g. in certain network environments), the implementation retries once and then enters a "router fallback" mode. In this mode, `code_interpreter()` raises a `RuntimeError` with the message *"direct command router connection"*. Always wrap interpreter usage in a try/except and fall back to `run_code()` as shown in the example above.
{% endhint %}

* **Timeout semantics differ by method:**
  * `exec_run(timeout_seconds=...)` — returns exit code `-1` if the command times out
  * `code_interpreter().run(timeout_seconds=...)` — the timeout is logged but **ignored** at the protocol level; session-level limits still apply
  * `process.wait(timeout_seconds=...)` — waits up to the specified duration for the streaming process to complete
* **`run_code` supports Python only.** The `language` parameter is accepted for API consistency, but only Python code is executed.
* **`verbose=True` can produce a lot of output.** When enabled, Modal's internal execution logs are printed to stdout. This is useful for debugging sandbox creation issues but noisy for production runs.
