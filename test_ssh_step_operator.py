#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["zenml"]
# ///
"""Manual test script for the SSH step operator.

Before running this script, set up a ZenML stack with an SSH step operator.
The remote host must have Docker and flock installed, and the SSH user must
be in the docker group.

Stack setup example
-------------------

1. Install the SSH integration:

    zenml integration install ssh --uv -y

2. Register a remote artifact store (e.g., S3):

    zenml artifact-store register s3-store \
        --flavor=s3 \
        --path=s3://my-bucket/zenml-artifacts

3. Register a remote container registry (e.g., DockerHub):

    zenml container-registry register dockerhub \
        --flavor=dockerhub \
        --uri=docker.io/<DOCKERHUB_USERNAME>

4. Register an image builder:

    zenml image-builder register local-builder --flavor=local

5. Register the SSH step operator:

    zenml step-operator register ssh-gpu-box \
        --flavor=ssh \
        --hostname=<REMOTE_HOST> \
        --username=<SSH_USER> \
        --ssh_key_path=~/.ssh/id_ed25519

6. Create and set the stack:

    zenml stack register ssh-stack \
        -a s3-store \
        -c dockerhub \
        -i local-builder \
        -s ssh-gpu-box \
        --set

7. Add the remote host key to known_hosts (if verify_host_key=True):

    ssh-keyscan -H <REMOTE_HOST> >> ~/.ssh/known_hosts

8. Run this test:

    uv run test_ssh_step_operator.py
"""

from zenml import pipeline, step
from zenml.integrations.ssh.flavors import SSHStepOperatorSettings


@step(step_operator=True)
def cpu_step() -> str:
    """Simple CPU-only step that runs on the remote host."""
    import platform

    info = f"Running on {platform.node()} ({platform.system()} {platform.machine()})"
    print(info)
    return info


@step(
    step_operator=True,
    settings={
        "step_operator": SSHStepOperatorSettings(
            gpu_indices=[0],
            use_gpu_locks=True,
        )
    },
)
def gpu_step() -> str:
    """GPU step that requests GPU 0 with locking.

    Uncomment the torch import lines below if PyTorch is available in
    your Docker image to verify GPU access.
    """
    # import torch
    # gpu_available = torch.cuda.is_available()
    # device_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    # info = f"GPU available: {gpu_available}, device: {device_name}"
    info = "GPU step executed (uncomment torch lines to verify GPU access)"
    print(info)
    return info


@pipeline
def ssh_test_pipeline():
    cpu_result = cpu_step()
    gpu_result = gpu_step()
    return cpu_result, gpu_result


if __name__ == "__main__":
    ssh_test_pipeline()
