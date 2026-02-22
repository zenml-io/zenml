---
description: Executing lightweight local sandbox sessions with Monty.
---

# Monty Sandbox

The Monty sandbox flavor uses [pydantic-monty](https://github.com/pydantic/pydantic-ai/tree/main/pydantic_monty) to provide lightweight, in-process sandbox sessions. It is intended for local execution scenarios where low overhead matters.

### When to use it

Use the Monty sandbox if you want:

* Local-only sandbox behavior with no remote infrastructure.
* Fast, lightweight sessions in the current execution environment.
* Snapshot and persistent-session capabilities for iterative development.
* A sandbox for testing and prototyping before moving to a remote provider.

### What Monty is (and is not)

{% hint style="info" %}
**Monty runs in-process, not in a container.** Unlike Daytona and Modal, Monty does not provision remote infrastructure. It uses `pydantic-monty` to execute Python code within the current Python process. The `image`, `cpu`, and `gpu` session parameters are accepted for API shape consistency, but they do **not** provision resources — they are recorded as metadata fields (`requested_image`, `requested_cpu`, etc.) for traceability.
{% endhint %}

This makes Monty ideal for:
* **Local development** — test your sandbox-using pipeline logic without cloud credentials
* **CI pipelines** — validate sandbox patterns without incurring cloud costs
* **Prototyping** — iterate on sandbox workflows before switching to a remote provider

### How to deploy it

To use the Monty sandbox flavor:

* Install the Monty integration:

  ```shell
  zenml integration install monty
  ```

* Register a sandbox component:

  ```shell
  zenml sandbox register monty-sb --flavor=monty
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox monty-sb
  ```

### Realistic pipeline example

This example demonstrates Monty's key features — code execution with inputs, error handling, a persistent interpreter, and snapshots:

```python
from zenml import step, pipeline
from zenml.sandboxes import SandboxCapability, SandboxExecError
from zenml.steps import get_step_context

@step(sandbox=True)
def monty_step() -> str:
    ctx = get_step_context()
    if ctx.sandbox is None:
        raise RuntimeError("No sandbox in the active stack.")

    with ctx.sandbox.session(
        timeout_seconds=60,
        env={"MY_VAR": "hello"},
    ) as sb:
        # Execute code with input variables
        result = sb.run_code(
            "x * y + 1",
            inputs={"x": 5, "y": 3},
        )
        print(f"Result: {result.output}")  # 16

        # check=True raises SandboxExecError on failures
        try:
            sb.run_code("1 / 0", check=True)
        except SandboxExecError:
            print("Caught expected division by zero error")

        # Persistent interpreter — state carries between calls
        with sb.code_interpreter() as interp:
            interp.run("counter = 0")
            interp.run("counter = counter + 1")
            result = interp.run("counter")
            print(f"Counter: {result.output}")  # 1

        # Snapshots capture the interpreter state
        snapshot = sb.snapshot()
        print(f"Snapshot available: {bool(snapshot)}")

        # Filesystem is not supported — check before calling
        if not ctx.sandbox.has_capability(SandboxCapability.FILESYSTEM):
            print("Filesystem not available (expected for Monty)")

    return str(result.output)

@pipeline
def my_monty_pipeline():
    monty_step()
```

### Configuration

#### Component config (`MontySandboxConfig`)

| Field | Default | Description |
| --- | --- | --- |
| `type_check` | `True` | Enable type checking in Monty execution |
| `raise_on_failure` | `True` | Raise exceptions on execution errors |

#### Step-level settings (`MontySandboxSettings`)

| Field | Default | Description |
| --- | --- | --- |
| `external_functions` | `None` | Map of declared external functions available to sandbox code |
| `type_check_stubs` | `None` | Type-checking stubs passed to the sandbox session |

Plus all the common settings inherited from `BaseSandboxSettings` (`timeout_seconds`, `image`, `cpu`, `memory_mb`, `gpu`, `env`, `secret_refs`, `network_policy`, `tags`, `forward_output_to_step_logs`).

### Capabilities

Monty currently advertises the following sandbox capabilities:

* `snapshots` — capture serialized interpreter state
* `persistent` — sessions retain state across commands

It does not support `filesystem`, `networking`, `tunnels`, `streaming`, `gpu`, or `exec_cancel`. Attempting to call unsupported methods (like `write_file`) raises a clear `NotImplementedError`.

### Execution model

Monty's execution model differs from remote providers in important ways:

**`run_code()` is the primary API.** Unlike Daytona and Modal where `exec_run` with shell commands is the natural entry point, Monty is Python-centric. Prefer `run_code()` with the `inputs` parameter for passing data into sandbox code:

```python
# Preferred — clear and explicit
result = sb.run_code("x ** 2 + y", inputs={"x": 3, "y": 1})

# Also works but less idiomatic for Monty
result = sb.exec_run(["python", "-c", "print(3 ** 2 + 1)"])
```

**`exec_run` maps commands to Python.** When you call `exec_run(["python", "-c", "print(42)"])`, Monty extracts the code from the last argument and executes it as Python. This works for simple cases but `run_code()` is more reliable and expressive.

### Snapshot semantics

The `snapshot()` method captures the serialized REPL state as a base64-encoded string:

```python
with sb.code_interpreter() as interp:
    interp.run("data = [1, 2, 3]")

snapshot = sb.snapshot()
# Returns a base64-encoded string of the interpreter state,
# or None if no REPL state exists yet
```

Session metadata records the snapshot byte size when state exists (`snapshot_bytes`).

### Gotchas and caveats

{% hint style="warning" %}
**`external_functions` and `code_interpreter()` are incompatible.** If you declare `external_functions` in your settings, calling `code_interpreter()` raises a `RuntimeError`. Use `run_code()` instead when external functions are needed.
{% endhint %}

* **Input keys must be valid Python identifiers.** Passing `inputs={"my-var": 1}` or `inputs={"123abc": 1}` raises a `ValueError`. Use valid Python names like `inputs={"my_var": 1}`.
* **Interpreter per-call `timeout_seconds` is ignored.** When you call `interpreter.run(code, timeout_seconds=10)`, the timeout is logged but not enforced at the per-call level. Session-level timeout limits still apply.
* **`run_code` supports Python only.** The `language` parameter is accepted for API consistency but only Python code is executed.
* **Cost metadata is always zero.** Since Monty runs in-process, `estimated_cost_usd` is always `0.0` in session metadata.
* **Resource parameters are metadata-only.** Passing `image="python:3.12"` or `gpu="1"` to `session()` records these as `requested_image`, `requested_gpu`, etc. in metadata, but does not allocate any infrastructure.
