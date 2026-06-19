# Robot Policy Training on Baseten 🤖

This example trains a **behavior-cloning policy** for a simple 2D reaching task
and runs the GPU-heavy training step as a **[Baseten](https://www.baseten.co/)
training job** via the ZenML Baseten step operator — while the rest of the
pipeline (data generation, preprocessing, evaluation, promotion) runs under your
normal orchestrator.

It's a compact, end-to-end illustration of the pattern a robotics team would use
for policy learning: collect demonstrations → train a policy on H100s → evaluate
against held-out demonstrations → promote the model when it clears a quality bar.

## The pipeline

```
generate_demonstrations          # scripted expert rollouts -> trajectory table
        │
   prepare_datasets              # shuffle + train/val split
        │  ┌──────────────┐
        ├──┤  train_set    ├────► train_policy        ← runs on Baseten (H100)
        │  └──────────────┘            │
        │                              ▼
        └──► val_set ──────────► evaluate_policy       ← validation MSE
                                       │
                                 promote_policy         ← promote if MSE ≤ threshold
```

Every step exchanges ZenML artifacts, logs rich metadata, and the run is tracked
under a `reaching_policy` ZenML Model so versions, metrics and promotion stage
are all visible in the dashboard — ideal for a live demo.

## Quick local run

No GPU or Baseten account required — the training step falls back to a NumPy
least-squares fit when PyTorch isn't installed:

```bash
pip install -r requirements.txt
python run.py --local
```

## Running the training step on Baseten

1. Install the integration and register a stack with the Baseten step operator, a
   remote artifact store, a container registry and an image builder:

   ```bash
   zenml integration install baseten
   zenml step-operator register baseten_operator \
       --flavor=baseten \
       --api_key=<YOUR_BASETEN_API_KEY> \
       --project=maven-robotics

   zenml stack register baseten_stack \
       -s baseten_operator \
       -a <REMOTE_ARTIFACT_STORE> \
       -c <REMOTE_CONTAINER_REGISTRY> \
       -i <IMAGE_BUILDER> \
       --set
   ```

2. Run the pipeline, sending only `train_policy` to Baseten:

   ```bash
   python run.py --step-operator baseten_operator --accelerator H100
   ```

The training step is built into a container, pushed to Baseten, executed on an
H100, and its status is streamed back to ZenML. A clickable link to the Baseten
job logs is attached to the step as metadata (`baseten_logs_url`).

> **Caching:** the example enables Baseten's persistent training cache
> (`enable_cache=True`) so model/dataset downloads are reused across runs. It is
> off by default in the operator. See the
> [step operator docs](https://docs.zenml.io/stacks/step-operators/baseten) for
> caching, checkpointing, secrets and multi-node training.

## Multi-node distributed training

For real multi-node distributed training, replace `train_policy` with a
[`CommandStep`](https://docs.zenml.io/how-to/steps-pipelines/command_steps) that
launches `torchrun`, and set `node_count > 1` on the operator settings. Baseten
provisions the nodes and injects `BT_GROUP_SIZE`, `BT_NODE_RANK`,
`BT_LEADER_ADDR` and `BT_NUM_GPUS`, which your command wires into the distributed
launcher.
