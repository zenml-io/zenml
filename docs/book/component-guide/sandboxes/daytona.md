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
  zenml sandbox register daytona-sb --flavor=daytona
  ```

* Attach it to a stack:

  ```shell
  zenml stack update <STACK_NAME> --sandbox daytona-sb
  ```

### Realistic pipeline example

This example demonstrates the key Daytona sandbox features in a single step — command execution, error handling, streaming output, file I/O, and a persistent code interpreter:

```python
from zenml import step, pipeline
from zenml.integrations.daytona.flavors import DaytonaSandboxSettings
from zenml.sandboxes import SandboxExecError
from zenml.steps import get_step_context

@step(
    sandbox=True,
    settings={
        "sandbox.daytona": DaytonaSandboxSettings(
            ephemeral=True,
            auto_stop_interval_minutes=20,
        )
    },
)
def daytona_step() -> str:
    ctx = get_step_context()
    if ctx.sandbox is None:
        raise RuntimeError("No sandbox in the active stack.")

    with ctx.sandbox.session(
        image="python:3.12",
        timeout_seconds=600,
        env={"MY_VAR": "hello"},
    ) as sb:
        # Run a command and capture stdout
        result = sb.exec_run(
            ["python", "-c", "import os; print(os.environ['MY_VAR'])"]
        )
        print(f"Output: {result.stdout.strip()}")

        # check=True raises SandboxExecError on non-zero exit
        try:
            sb.exec_run(
                ["python", "-c", "import sys; sys.exit(3)"],
                check=True,
            )
        except SandboxExecError as e:
            print(f"Caught expected error: exit code {e.result.exit_code}")

        # Streaming output — read a known number of lines
        process = sb.exec_streaming(
            ["python", "-u", "-c",
             "for i in range(3): print(f'line {i}')"]
        )
        for line in process.stdout_iter():
            print(line, end="")
        process.wait(timeout_seconds=30)

        # File operations
        sb.write_file("/tmp/example.txt", "sandbox file content")
        content = sb.read_file("/tmp/example.txt").decode("utf-8")

        # Persistent code interpreter — state carries between calls
        with sb.code_interpreter() as interp:
            interp.run("counter = 0")
            interp.run("counter += 1")
            result = interp.run("print(counter)")

    return content

@pipeline
def my_daytona_pipeline():
    daytona_step()
```

### Configuration

#### Component config defaults (`DaytonaSandboxConfig`)

These are set when you register the sandbox and serve as the lowest-priority defaults:

| Field | Default | Description |
| --- | --- | --- |
| `default_image` | `python:3.12` | Base image for sandbox workspaces |
| `default_cpu` | `2` | CPU cores allocated to the sandbox |
| `default_memory_gb` | `4` | Memory in GB allocated to the sandbox |
| `default_disk_gb` | `8` | Disk space in GB for the workspace |
| `raise_on_failure` | `True` | Whether sandbox failures raise exceptions |

You can set these at registration time:

```shell
zenml sandbox register daytona-sb \
    --flavor=daytona \
    --default_cpu=4 \
    --default_memory_gb=8
```

#### Step-level settings (`DaytonaSandboxSettings`)

These override component defaults and are set per-step via the `settings` parameter:

| Field | Default | Description |
| --- | --- | --- |
| `api_url` | `None` | Custom Daytona API endpoint |
| `target` | `None` | Target runtime where the sandbox should run |
| `ephemeral` | `None` | When `True`, sessions are automatically deleted when stopped |
| `auto_stop_interval_minutes` | `None` | Inactivity threshold before Daytona auto-stops a session. If unset, a value is computed from `timeout_seconds` |
| `auto_delete_interval_minutes` | `None` | Delay before auto-deleting a stopped session |

Plus all the common settings inherited from `BaseSandboxSettings` (`timeout_seconds`, `image`, `cpu`, `memory_mb`, `gpu`, `env`, `secret_refs`, `network_policy`, `tags`, `forward_output_to_step_logs`).

### Configuration precedence

Settings are resolved in this order (first match wins):

1. **Session call arguments**: `ctx.sandbox.session(image="python:3.11", cpu=4, ...)`
2. **Step settings**: `@step(settings={"sandbox.daytona": DaytonaSandboxSettings(cpu=2)})`
3. **Component config defaults**: values from `zenml sandbox register ...`

**Environment variable merge behavior:**

Secret references are resolved first from the ZenML secrets store, then explicit `env` values are layered on top. This means if a secret defines `DB_PASSWORD=secret_value` and you also pass `env={"DB_PASSWORD": "override"}`, the explicit value wins.

**Tags** follow the same precedence: step-level tags are used as the base, then session-level tags override any matching keys.

### Capabilities

Daytona currently advertises the following sandbox capabilities:

* `filesystem` — read/write files inside the sandbox
* `streaming` — real-time stdout/stderr output via `exec_streaming`
* `persistent` — sessions retain state across multiple commands

### Gotchas and caveats

{% hint style="warning" %}
**GPU setting accepts numeric values only.** If you pass a string like `"A10G"` as the `gpu` setting, it will be silently ignored with a warning in the logs. Use a numeric value like `"1"` or `1` to request GPU count.
{% endhint %}

{% hint style="info" %}
**Network policy is forwarded but not a capability.** You can pass `network_policy=NetworkPolicy(block_network=True, cidr_allowlist=["10.0.0.0/8"])` and Daytona will forward these as creation-time parameters (`network_block_all`, `network_allow_list`). However, Daytona does not advertise `networking` as a capability — this means there is no interactive networking API, just upfront access controls.
{% endhint %}

* **Cost metadata is not yet available.** The Daytona provider implementation currently reports `estimated_cost_reason: "not available in daytona provider v1"` in session metadata. Cost estimates may be added in future versions.
* **Auto-stop interval computation.** If you don't set `auto_stop_interval_minutes` explicitly, it is automatically computed from `timeout_seconds` using the formula in `_resolve_auto_stop_interval()`. This ensures the sandbox doesn't idle unnecessarily but also doesn't get stopped before your timeout expires.
* **`run_code` supports Python only.** Calling `run_code(code, language="javascript")` or any non-Python language will not work as expected.
* **Daytona SDK compatibility.** The implementation includes fallback paths for different Daytona SDK versions. If streaming output appears buffered rather than real-time, this may be due to an older SDK version — check that you have the latest `daytona-sdk` installed.
