---
description: Run prime-rl on your own Kubernetes with ZenML bookends — gate evals, ingest rollout traces, register checkpoints — no matter who launched the training.
icon: dumbbell
---

# Run prime-rl on your own Kubernetes, with receipts

[prime-rl](https://github.com/PrimeIntellect-ai/prime-rl) is Prime Intellect's open-source RL post-training stack. It owns the training loop — a policy trainer, a vLLM inference server, and an orchestrator process that ties them together — and it knows how to launch itself at scale. ZenML does **not** try to replace that. What ZenML adds is the *bookends*: the cached eval that decides whether a run is worth starting, and the trace ingestion, checkpoint registration, and lineage that turn a finished training run into queryable artifacts on your dashboard.

The important property is that these bookends are **file-based**, so they work identically no matter who launched prime-rl. Whether the trainer ran as a ZenML step pod, a SLURM job, or a Helm release, ZenML reads the same `traces.jsonl` and `weights/step_N` directories off shared storage. Scheduling is prime-rl's job; the integration surface is files.

{% hint style="info" %}
prime-rl ships a maintained Kubernetes Helm chart, but its hosted documentation link for it (`docs.primeintellect.ai/prime-rl/kubernetes`) is a dead link as of 2026-07-15 — the page does not exist. This guide is the version that link never wrote.
{% endhint %}

## The honest distribution table

There is no single "run prime-rl on Kubernetes" answer, because how you launch depends on how many nodes you need. Pick the row that matches your hardware.

| Shape | Who launches training | ZenML's role |
|---|---|---|
| **Single-node K8s** (1 node, ≤8 GPU) | ZenML step pod: a `CommandStep` with pod settings and `nvidia.com/gpu: N` | Full story — placement *and* bookends. This is the demo shape. |
| **SLURM multi-node** | prime-rl native, via its `[slurm]` block | Bookends only — a submit-and-poll step, then ingest off shared storage. |
| **K8s multi-node, standing deployment** | prime-rl's own Helm chart (StatefulSets per component, `autoStart: false`) | Bookends only — outputs land on the shared PVC an in-cluster pipeline reads directly. |

## What you provide vs. what ZenML deploys

ZenML installs **nothing standing** on your cluster — no operators, CRDs, or controllers. Everything it creates is per-run and garbage collected:

| ZenML creates (per run, ephemeral) | Dies when |
|---|---|
| orchestrator pod, one pod per step | run / step ends |
| sandbox pods (one per eval trial) | trial ends |
| trainer indexed Job + headless Service; served checkpoints as `KubernetesPodService` pods | with the Job / at the service's max-lifetime deadline |
| the pipeline Docker image (built at submit, pushed to *your* registry) | stays in your registry |

What must exist **before**, once — and this list is nearly identical to what prime-rl's own Helm chart demands, so it is table stakes for the workload, not ZenML overhead:

1. **GPU nodes with the NVIDIA device plugin / GPU Operator** installed, so `nvidia.com/gpu` is schedulable. ZenML never installs this.
2. **An RWX StorageClass and a PVC created from it** (NFS/EFS/CephFS). ZenML *mounts* existing volumes via `pod_settings`; it does not provision them. This volume carries the trainer↔orchestrator transport — and, on LoRA runs, the weight broadcast fallback — so forgetting it produces a "trainer runs, orchestrator sees nothing" failure.
3. **A container registry** the cluster can pull from (plus `imagePullSecrets` for private registries), registered as your ZenML container registry.
4. **A ZenML server reachable from inside the cluster** — every pod reports artifacts and status to it — and stack credentials with RBAC to create/delete `jobs`, `pods`, and `services` in the namespace.
5. **The ZenML stack**: Kubernetes orchestrator + sandbox + step operator, artifact store, container registry, wired through a service connector.
6. **Two images pushed**: the task/scorer image your eval tasks pin, and — the one most people miss — an image with **prime-rl inside it** for the trainer and serving pods. The ZenML-built pipeline image does not contain torch/vllm/prime-rl. Use prime-rl's published image as the parent: `DockerSettings(parent_image="primeintellect/prime-rl:main", requirements=["zenml==<your pin>"])` — the explicit zenml requirement is mandatory with a custom parent image. Service pods (`KubernetesPodService`) can pin an image directly, since they never run ZenML code.
7. **Secrets** (HF token, wandb, model API keys) via ZenML secrets or Kubernetes secrets referenced from `pod_settings`.
8. **Networking reality check**: pod-to-pod traffic must be open (default CNI behavior). NetworkPolicies that block it break the NCCL weight broadcast and the orchestrator→inference HTTP path — the same assumption prime-rl's Helm chart makes.

### Single-node: ZenML launches the trainer

On one node you don't need prime-rl's distributed machinery, so ZenML can launch training directly as a [`CommandStep`](https://github.com/zenml-io/zenml/tree/main/examples/agentic_rl). A command step runs an opaque command in its pod — it owns its own process launch, ZenML just schedules the pod and places it:

```python
from zenml.steps import CommandStep
from zenml.config import ResourceSettings

train_prime_rl = CommandStep(
    command=["uv", "run", "--project", PRIME_RL_DIR, "rl", "@", "configs/rl.toml",
             "--output-dir", RUN_OUTPUT_DIR, "--ckpt"],
    name="train_prime_rl",
    settings={"resources": ResourceSettings(gpu_count=2)},
)
```

Place the pod on a GPU node pool with the Kubernetes orchestrator's `pod_settings` (node selectors, tolerations) — the same pattern the sandbox flavor documents under [pod settings](https://docs.zenml.io/stacks/sandboxes/kubernetes). prime-rl defaults to two GPUs (one trainer, one inference); single-GPU is an unmerged upstream PR, so plan for two.

### Multi-node: prime-rl launches, ZenML bookends

Past one node, prime-rl owns launch. For **SLURM**, fill in its `[slurm]` block and let it submit; your ZenML step is a submit-and-poll wrapper that waits for the job, then hands `output_dir` to the ingestion step. For **K8s multi-node**, install prime-rl's Helm chart as a standing deployment (`helm install`, `autoStart: false`, then `exec` in to start the run). The chart provisions a StatefulSet per component, an RWX PVC mounted at `/data`, and `$INFERENCE_URL`-based service discovery between them. Because everything writes to that shared PVC, a ZenML pipeline running in the same cluster reads the outputs directly — no copy step.

In both cases ZenML never touches the training topology. It reads what training left on disk.

## The bookends pattern

Every tier, whoever launched the trainer, has the same four beats.

**1. Gate the eval before you spend GPUs.** Run a cheap eval first and only start training if the current model is worth improving. Cache it so re-runs are free. Gate on the *error count first*, then the reward — a run where every trial errored can look like reward `0.0`, which is not the same as a genuinely low score:

```python
@step
def gate(eval_result: EvalResult) -> None:
    if eval_result.n_errored == eval_result.n_total:
        raise RuntimeError("All eval trials errored — infra failure, not a low score.")
    if eval_result.mean_reward >= TARGET:
        raise RuntimeError(f"Model already at {eval_result.mean_reward}; nothing to train.")
```

Because command steps have no data inputs, the gate connects to the trainer with control flow, not a data edge: `train_prime_rl.after(gate_step)`.

**2. Train.** Either the `CommandStep` above (single node) or an external launch (SLURM/Helm). ZenML's job ends at "the pod/job ran"; the training *outcome* is wandb's business, not the pipeline's.

**3. Ingest the rollout traces after.** prime-rl appends one full `Rollout` record per rollout to `output_dir/rollouts/step_{n}/{train,eval}/{all,effective}/traces.jsonl`. A normal Python step reads them into one table artifact — rows, not steps, one artifact version per training step:

```python
ingest_rollout_traces(output_dir=RUN_OUTPUT_DIR).after(train_prime_rl)
```

Each record carries the reward, the **`runtime.id`** (the sandbox session the rollout ran in — this is the join key from reward back to sandbox image), the tool definitions, per-node timings, token usage, and the policy version. It does **not** carry advantages, tokens, logprobs, or masks: those are `exclude=True` on prime-rl's `Rollout` and `to_record()` does not re-add them. If you need the training tensors in your lineage, that requires the upstream monitors PR, not file ingestion — do not promise it from traces alone.

**4. Register the checkpoint.** prime-rl writes HuggingFace-format checkpoints to `outputs/weights/step_N`. The same ingestion step registers that directory as a ZenML artifact, so the model version chains to the traces that produced it: reward ↔ sandbox session ↔ image digest ↔ taskset ↔ checkpoint, walkable on the dashboard.

The [`examples/agentic_rl`](https://github.com/zenml-io/zenml/tree/main/examples/agentic_rl) example is the working version of all four beats, with a `--smoke` tier that needs no GPU and a `--train` tier that shells out to a prime-rl checkout.

## What ZenML does not do here

Be honest with yourself about the boundary:

* **ZenML does not orchestrate multi-node training.** Past one node, prime-rl's SLURM integration or Helm chart owns launch, health, and rendezvous. ZenML reads outputs; it does not schedule GPUs across nodes.
* **Live training curves are wandb's job.** The traces artifact is a post-hoc record for lineage and regression comparison, not a live dashboard. prime-rl already streams to wandb during the run.
* **A solo researcher running one experiment should just use `uv run rl`.** The bookends earn their keep when you run this *repeatedly* — gating spend, comparing checkpoints across runs, and answering "which sandbox image produced this reward" months later. For a one-off, the CLI is less friction, and that is the right call.

## Where this is heading

The single-node `CommandStep` shape and the multi-node bookends together point at a gap: ZenML can place *one* pod for a command step, but a distributed trainer wants a *pod set* it owns for the run's lifetime. The Kubernetes step operator ships exactly that: `KubernetesStepOperatorSettings(node_count=N)` on a command step materializes an indexed Job with a job-owned headless service — see the step-operator docs for the mechanics. This guide's bookends work regardless of who launches.
