# Robot Policy Training on Baseten 🤖

This example trains a **behavior-cloning policy** for a simple 2D reaching task and runs the
GPU training as a **[Baseten](https://www.baseten.co/) training job** via the ZenML Baseten step
operator, while the rest of the pipeline runs under your normal orchestrator.

It's a compact illustration of the pattern a robotics team would use: prepare a training run →
train a policy on H100s → (in a real setup) evaluate and promote the model.

## The pipeline

```
prepare_training_run            # regular ZenML step, runs in the orchestrator
        │  (versions the demonstration dataset as a ZenML artifact)
        ▼
   train  (CommandStep)         # opaque GPU command, runs on Baseten (H100)
```

`prepare_training_run` is a normal `@step` that generates the expert demonstrations from a
`seed` and **versions them as a ZenML artifact** (inspectable in the dashboard). `train` is a
[`CommandStep`](https://docs.zenml.io/how-to/steps-pipelines/command_steps) — an opaque command
(`python /tmp/train.py`, or `torchrun ...` for multi-node) that Baseten runs on a GPU. The whole
run is tracked under a `reaching_policy` ZenML Model.

### How the two steps connect

A `CommandStep` runs as an opaque job and **cannot receive ZenML artifacts at runtime**, so the
prep step and the training command are connected by a **shared seed** rather than by passing the
dataset object: both call the same `make_demonstrations(seed, num_samples)` routine (defined once
in `training_script.py` and imported by the prep step), so they provably train on the *identical*
data. The `--seed`, `--num-samples` and `--epochs` flags are baked into the training command as
environment variables, so they genuinely drive the job — not just the prep step's metadata.

> In production you would instead have the prep step write the versioned dataset to a shared
> bucket and the command stream it from there (the standard Baseten data-loading pattern); the
> seed approach keeps this example credential-free and fully reproducible.

## Why a `CommandStep` (and not a regular `@step`)?

This is the **recommended Baseten pattern**, and it's also shaped by two Baseten **organization
entitlements** you should know about:

| Capability | Needs from Baseten | Used by |
|---|---|---|
| **Custom base images** | Org entitlement (contact Baseten support) | Regular `@step`s on Baseten |
| **Multi-node instance types** | Org entitlement (contact Baseten support) | `node_count > 1` |

* A **regular `@step`** runs the ZenML entrypoint, so its container must contain `zenml`, your
  code and dependencies — i.e. a **custom image**. If your Baseten org does not have *custom base
  images* enabled, those jobs are rejected (`Custom base images not supported for your
  organization`). This example therefore uses a `CommandStep` on a **stock public PyTorch image**
  (`skip_build=True`), which every org can pull — no custom image is built or pushed.
* **Multi-node** (`node_count > 1`) additionally requires your org to have **multi-node instance
  types** enabled; otherwise job creation returns a `400`.

So on a fresh Baseten org, the `CommandStep` + public-image single-node path below works out of
the box; the regular-`@step` and multi-node paths need the corresponding entitlement enabled
first. None of this is a ZenML limitation — the operator builds, submits, polls, cancels and
records metadata for all of these; the gates are on the Baseten account.

## Run it

```bash
pip install -r requirements.txt
zenml integration install baseten

# Local smoke test (runs the training command locally):
python run.py --local

# Single-node training on Baseten (one H100) — works on any org:
python run.py --step-operator baseten_operator --accelerator H100

# Multi-node distributed training (requires multi-node instance types enabled):
python run.py --step-operator baseten_operator --node-count 4 --gpu-count 8
```

Register a stack with the Baseten step operator, a remote artifact store, a container registry
and an image builder first:

```bash
zenml step-operator register baseten_operator \
    --flavor=baseten --api_key=<YOUR_BASETEN_API_KEY> --project=maven-robotics

zenml stack register baseten_stack \
    -s baseten_operator -a <REMOTE_ARTIFACT_STORE> \
    -c <REMOTE_CONTAINER_REGISTRY> -i <IMAGE_BUILDER> --set
```

For single-node `CommandStep` runs on a public image, the container registry and image builder
are not exercised (nothing is built), but they are part of a complete Baseten stack and are
needed as soon as you build custom images.

## How multi-node works

When `--node-count > 1`, Baseten provisions that many identical nodes and injects
`BT_GROUP_SIZE`, `BT_NODE_RANK`, `BT_LEADER_ADDR` and `BT_NUM_GPUS`. The command wires those into
`torchrun` so each node joins the same distributed job — see `training_script.py` (which reads the
rank/world topology) and `pipelines/training.py` (which builds the `torchrun` command).

See the [step operator docs](https://docs.zenml.io/stacks/step-operators/baseten) for caching,
checkpointing, secrets and the full settings reference.
