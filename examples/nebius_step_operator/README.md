# Nebius Serverless step operator

This experimental example prepares data locally, runs `score_on_gpu` in a
single-GPU Nebius Serverless Job, and loads its output locally through ZenML's
artifact store. Expected output: `[5.0, 25.0]`.

## Setup

Use the `develop` checkout containing this integration. From the repository root:

```shell
uv pip install -e .
zenml integration install nebius s3
uv build --wheel --out-dir examples/nebius_step_operator/wheels
cd examples/nebius_step_operator
```

Use a Python version supported by this checkout. The worker parent image contains
PyTorch with CUDA 12.8; the Dockerfile installs the same ZenML checkout wheel into
that image. ZenML then builds the step image, installs stack requirements, and
pushes it to your registered remote registry. The example requests `linux/amd64`
and sets `UV_SYSTEM_PYTHON=1` for uv when installing stack requirements into the
PyTorch parent image's existing Conda Python.
A working Docker builder and registry push credentials are required.

Connect to a ZenML server reachable from both the launcher and your Nebius subnet.
Follow the [component guide](../../docs/book/component-guide/step-operators/nebius.md)
to configure a stack with:

- The local orchestrator.
- A remote artifact store, with credentials usable inside the Job.
- A remote container registry and an image builder.
- A `nebius` step operator named `nebius-gpu`, with your project and subnet.

The example explicitly selects `gpu-l40s-a` / `1gpu-8vcpu-32gb`. Choose a supported
single-GPU platform/preset for your project if these are unavailable. Configure
private image-pull credentials separately from registry push credentials.
Keep launcher credentials outside this directory and Docker build context.

## Run

The following command creates billable GPU compute in your Nebius project:

```shell
python run.py
```

Run the command again to exercise ZenML caching: unchanged steps should use
existing artifacts without creating another Job. To rerun compute intentionally,
disable caching using ZenML pipeline options.

The launcher logs the Job ID and a `nebius ai job logs <job-id> --follow` command.
The `nebius_submission` step metadata retains submission identity and cleanup
observations. Ctrl-C attempts to cancel an acknowledged Job. Inspect the Job and
underlying Compute resources if cancellation or submission is uncertain.

## Validation status

The integration has local lifecycle, SDK serialization, and bootstrap tests.
This CUDA example has not been executed on Nebius. Before production use, validate
GPU execution, artifact round-trips, private pulls, token renewal, cancellation,
and VM/boot-disk cleanup with your own project and credentials. Provider timeout
and Job completion alone do not prove deletion of all underlying resources.
