---
description: Executing individual steps on a remote host via SSH and Docker.
---

# SSH Step Operator

The SSH step operator allows you to execute individual ZenML steps on a remote Linux host via SSH. Steps run inside Docker containers on the remote machine, with optional GPU selection and per-GPU mutual exclusion via `flock` locks. This is ideal for teams that have dedicated GPU machines they want to use for training without needing a full cluster orchestration platform.

### When to use it

You should use the SSH step operator if:

* You have a **dedicated remote machine** (e.g., a GPU workstation or server) reachable via SSH.
* You want to run compute-heavy steps (training, inference) on that machine while keeping your orchestrator lightweight.
* You need **per-GPU mutual exclusion** so concurrent pipeline steps don't compete for the same GPU.
* You prefer a simple setup without Kubernetes or cloud-managed services.

### How to deploy it

The SSH step operator connects to an existing remote host; it does not provision infrastructure. Your remote host must meet these requirements:

* **Linux** operating system (the wrapper script relies on Linux tooling like `flock`).
* **Docker** installed and accessible to the SSH user (the user should be in the `docker` group).
* **`flock`** installed (part of `util-linux`, pre-installed on most Linux distributions).
* **Network reachability** from the machine running your orchestrator to `hostname:port` over SSH.
* If using GPUs: the **NVIDIA Container Toolkit** must be installed so Docker supports `--gpus`.

### How to use it

To use the SSH step operator, you need:

* The ZenML `ssh` integration installed. If you haven't done so, run:

    ```shell
    zenml integration install ssh
    ```

    This installs [paramiko](https://www.paramiko.org/), the Python SSH library used under the hood.

* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack (the remote container cannot access local files).

* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) to store the Docker images that will be pulled on the remote host.

* An [image builder](https://docs.zenml.io/stacks/image-builders/) to build the Docker images for your steps.

We can then register the step operator. **At least one of** `ssh_key_path` **or** `ssh_private_key` **must be provided** for authentication.

**Using a key file:**

```shell
zenml step-operator register <NAME> \
    --flavor=ssh \
    --hostname=<HOST> \
    --username=<USER> \
    --ssh_key_path=~/.ssh/id_ed25519
```

**Using a key stored in a ZenML secret:**

```shell
zenml secret create ssh_secret \
    --private_key='<KEY_CONTENT>' \
    --passphrase='<PASSPHRASE>'

zenml step-operator register <NAME> \
    --flavor=ssh \
    --hostname=<HOST> \
    --username=<USER> \
    --ssh_private_key={{ssh_secret.private_key}} \
    --ssh_key_passphrase={{ssh_secret.passphrase}}
```

We can then add the step operator to our active stack:

```shell
zenml stack update -s <NAME>
```

Once you have added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator:

```python
from zenml import step


@step(step_operator="<NAME>")
def trainer(...) -> ...:
    """Train a model on the remote host."""
    # This step will be executed via SSH + Docker
```

{% hint style="info" %}
ZenML will build a Docker image which includes your code and use it to run your steps on the remote host. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### What happens at runtime

When a step runs via the SSH step operator:

1. ZenML builds and pushes the step image using your stack's image builder and container registry.
2. The step operator opens an SSH connection to the remote host.
3. **Preflight checks** verify that `docker` and `flock` are available.
4. An **env-file** (with step environment variables) and a **wrapper script** are uploaded to the remote working directory.
5. The Docker image is **pulled** on the remote host.
6. The wrapper script is executed, which optionally acquires GPU locks, then runs the container with `docker run`.
7. Logs are **streamed back** in real time to your local output.
8. The env-file and script are automatically cleaned up on exit.

### GPU execution and locking

The SSH step operator has built-in support for GPU selection and mutual exclusion.

#### Selecting GPUs

Use the `gpu_indices` setting to specify which GPU devices to expose to the container:

```python
from zenml import step
from zenml.integrations.ssh.flavors import SSHStepOperatorSettings

ssh_settings = SSHStepOperatorSettings(
    gpu_indices=[0, 1],
    use_gpu_locks=True,
    docker_run_args=["--shm-size=2g"],
)


@step(
    step_operator="<NAME>",
    settings={"step_operator": ssh_settings},
)
def train():
    """Train with GPUs 0 and 1."""
    ...
```

GPU indices are passed to Docker as `--gpus "device=0,1"`. They must be non-negative integers matching the device indices reported by `nvidia-smi` on the remote host.

#### Per-GPU mutual exclusion

When `use_gpu_locks` is `True` (the default) and `gpu_indices` is set, the wrapper script acquires file-based `flock` locks for each GPU before starting the container:

* Lock files are created in `gpu_lock_dir` (default: `/tmp/zenml-gpu-locks`), named `gpu-0.lock`, `gpu-1.lock`, etc.
* Locks are acquired in **sorted index order** to prevent deadlocks.
* Locks are held for the **entire lifetime** of the `docker run` process and released automatically on exit.
* If another step is already using a GPU, the new step **blocks** until the lock is available.

This prevents concurrent pipeline steps from oversubscribing the same physical GPU.

#### CPU-only execution

If `gpu_indices` is not set (the default), the step runs without GPU access and no locks are acquired:

```python
ssh_settings = SSHStepOperatorSettings()  # CPU-only, no locks

@step(step_operator="<NAME>", settings={"step_operator": ssh_settings})
def preprocess():
    ...
```

### Configuration options

#### Step Operator Configuration (set during registration)

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `hostname` | str | Yes | - | Hostname or IP of the remote SSH server |
| `username` | str | Yes | - | SSH username (must have Docker permissions) |
| `port` | int | No | `22` | SSH port on the remote host |
| `ssh_key_path` | str | No* | - | Path to SSH private key file (RSA, Ed25519, ECDSA) |
| `ssh_private_key` | str | No* | - | SSH private key content (supports `{{secret.key}}` references) |
| `ssh_key_passphrase` | str | No | - | Passphrase for encrypted private key (supports `{{secret.key}}`) |
| `verify_host_key` | bool | No | `True` | Verify remote host key against known_hosts |
| `known_hosts_path` | str | No | - | Path to known_hosts file (defaults to system known_hosts) |
| `connection_timeout` | float | No | `10.0` | SSH connection timeout in seconds |
| `keepalive_interval` | int | No | `30` | Seconds between SSH keepalive packets (0 to disable) |
| `remote_workdir` | str | No | `/tmp/zenml-ssh` | Directory for temporary files on the remote host |
| `gpu_lock_dir` | str | No | `/tmp/zenml-gpu-locks` | Directory for per-GPU lock files |
| `docker_binary` | str | No | `docker` | Path to Docker binary on the remote host |

\* At least one of `ssh_key_path` or `ssh_private_key` must be provided.

#### Step Settings (per-step configuration)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `gpu_indices` | list[int] | `None` | GPU device indices to expose via `--gpus` flag |
| `use_gpu_locks` | bool | `True` | Acquire per-GPU flock locks (only when `gpu_indices` is set) |
| `docker_run_args` | list[str] | `None` | Additional `docker run` arguments (e.g., `["--shm-size=2g"]`) |

{% hint style="warning" %}
Do not include secrets in `docker_run_args` as they may appear in process listings on the remote host.
{% endhint %}

### Security notes

#### Host key verification

By default, `verify_host_key` is `True`, which uses paramiko's **RejectPolicy** to reject connections to unknown hosts. This protects against man-in-the-middle attacks.

If you haven't connected to the remote host before, add its host key first:

```shell
ssh-keyscan -H <HOST> >> ~/.ssh/known_hosts
```

For ephemeral or test hosts, you can set `verify_host_key=False` to auto-accept unknown host keys (less secure).

#### Secrets handling

* The env-file uploaded to the remote host is created with **`0600` permissions** (owner read/write only) and is **automatically deleted** after the step completes.
* Use ZenML secrets with `{{secret.key}}` syntax for `ssh_private_key` and `ssh_key_passphrase` to avoid storing credentials in plaintext.

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-ssh/) for the full API reference.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
