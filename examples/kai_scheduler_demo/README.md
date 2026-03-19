# ZenML + KAI-Scheduler GPU Demo

> **KubeCon demo** — Showcasing how ZenML integrates with
> [NVIDIA KAI-Scheduler](https://github.com/NVIDIA/KAI-Scheduler) for
> advanced GPU scheduling: queue-based fair-share, gang scheduling, GPU
> time-slicing, and topology-aware placement.

---

## What This Demo Shows

| Feature | Mechanism |
|---|---|
| **Queue-based scheduling** | `kai_queue` assigns every step pod to a named KAI leaf queue |
| **GPU fair-share** | KAI enforces quotas and `overQuotaWeight` across queues |
| **Priority + preemption** | `kai_priority_class` maps to a `PriorityClass`; KAI preempts lower-priority pods |
| **GPU time-slicing** | `kai_gpu_fraction` sets the `gpu-fraction` annotation for shared GPU allocation |
| **Gang scheduling** | `kai_pod_group_name` creates a `PodGroup` CRD; KAI schedules all pods atomically |
| **Topology awareness** | `kai_topology_constraint` in the PodGroup controls rack/node-level placement |

### Pipeline

```
cuda_matrix_benchmark ──▶ pytorch_cnn_train
```

- **Step 1 — `cuda_matrix_benchmark`**: Allocates two N×N matrices on GPU,
  runs a timed `torch.mm`, and logs GFLOPS + GPU memory usage to ZenML.
- **Step 2 — `pytorch_cnn_train`**: Trains a 2-conv-layer CNN on synthetic
  image data for N epochs, logging per-epoch loss to the ZenML dashboard.

---

## Prerequisites

### 1. Install KAI-Scheduler

```bash
# Add the NVIDIA Helm chart repository
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia/kai-scheduler
helm repo update

# Install KAI-Scheduler into your cluster
helm install kai-scheduler nvidia/kai-scheduler \
  --namespace kai-scheduler \
  --create-namespace
```

Verify the CRDs are available:

```bash
kubectl get crd | grep scheduling.run.ai
# Should list: podgroups, queues, ...
```

### 2. Apply Queues and Priority Classes

```bash
kubectl apply -f k8s/priority-classes.yaml
kubectl apply -f k8s/queues.yaml

# Verify
kubectl get queues.scheduling.run.ai
kubectl get priorityclasses | grep -E "build|train|inference"
```

### 3. Register a ZenML Stack

```bash
# Register the Kubernetes orchestrator (adjust context/namespace as needed)
zenml orchestrator register kai-k8s-orchestrator \
  --flavor=kubernetes \
  --kubernetes_namespace=zenml \
  --kubernetes_context=$(kubectl config current-context)

# Register remaining stack components (artifact store, container registry)
zenml artifact-store register ... 
zenml container-registry register ...

# Register and activate the full stack
zenml stack register kai-demo-stack \
  -o kai-k8s-orchestrator \
  -a <your-artifact-store> \
  -c <your-container-registry> \
  --set
```

---

## Running the Demo

### Full GPU Mode (KAI-Scheduler, dedicated GPU)

```bash
python run.py --config kai_demo.yaml
```

Each step pod is:
- Scheduled by `kai-scheduler` (not the default Kubernetes scheduler)
- Assigned to the `default-queue` leaf queue
- Given the `train` PriorityClass
- Requesting `nvidia.com/gpu: 1`

### GPU Sharing Mode (KAI time-slicing)

```bash
python run.py --config kai_demo_gpu_sharing.yaml
```

Each step pod gets 50% of a GPU via KAI's GPU sharing mechanism. No
`nvidia.com/gpu` resource request is needed — KAI handles the allocation
via the `gpu-fraction: 0.5` pod annotation.

### Local / CPU Mode (no KAI, no GPU)

```bash
python run.py --config kai_demo_local.yaml
```

Runs on any Kubernetes cluster without KAI-Scheduler or GPUs. Useful
for smoke-testing the pipeline logic locally (e.g., `kind`, `minikube`).

### Disable Caching

```bash
python run.py --config kai_demo.yaml --no-cache
```

---

## KAI-Scheduler Settings Reference

All settings live under `settings.orchestrator.kubernetes` in your YAML
config or inline on a `@step` decorator:

```python
from zenml.integrations.kubernetes.flavors import KubernetesOrchestratorSettings

@step(settings={
    "orchestrator.kubernetes": KubernetesOrchestratorSettings(
        kai_queue="default-queue",
        kai_priority_class="train",
        kai_gpu_fraction=0.5,        # OR kai_gpu_memory=4096 (MiB)
        kai_pod_group_name="my-group",
        kai_pod_group_min_members=2,
        kai_preemptibility="preemptible",
        kai_topology_constraint={
            "requiredTopologyLevel": "rack",
            "topology": "cluster-topology",
        },
    )
})
def my_gpu_step() -> None:
    ...
```

| Field | Type | Description |
|---|---|---|
| `kai_queue` | `str` | **Activates KAI.** Assigns pod to this leaf queue. Sets `schedulerName=kai-scheduler` automatically. |
| `kai_gpu_fraction` | `float` (0–1] | Fraction of GPU for time-slicing. Mutually exclusive with `kai_gpu_memory`. |
| `kai_gpu_memory` | `int` (MiB) | GPU memory for time-slicing. Mutually exclusive with `kai_gpu_fraction`. |
| `kai_priority_class` | `str` | Kubernetes PriorityClass name. |
| `kai_preemptibility` | `str` | `'preemptible'` or `'non-preemptible'` (PodGroup only). |
| `kai_pod_group_name` | `str` | PodGroup CRD name — enables gang scheduling. |
| `kai_pod_group_min_members` | `int` | Minimum pods for gang scheduling gate. |
| `kai_topology_constraint` | `dict` | `{'requiredTopologyLevel': '...', 'topology': '...'}` (PodGroup only). |

---

## How It Works Internally

When `kai_queue` is set, `KubernetesOrchestrator._apply_kai_settings_to_pod_settings()`
runs **before** each pod manifest is built and immutably merges:

```
kai_queue        → pod labels["kai.scheduler/queue"]
                 → pod spec.schedulerName = "kai-scheduler"
kai_gpu_fraction → pod annotations["gpu-fraction"]
kai_gpu_memory   → pod annotations["gpu-memory"]
kai_priority_class → pod spec.priorityClassName
```

When `kai_pod_group_name` is also set, the orchestrator calls
`kube_utils.create_kai_pod_group()` via the Kubernetes Custom Objects API
before submitting any jobs. The PodGroup CRD acts as the gang-scheduling
token that KAI-Scheduler uses to hold all pods until `minMember` can be
allocated simultaneously.

---

## Observing the Demo

```bash
# Watch pods being scheduled by kai-scheduler
kubectl get pods -n zenml -w

# Verify the KAI scheduler name on a pod
kubectl get pod <pod-name> -n zenml -o jsonpath='{.spec.schedulerName}'
# → kai-scheduler

# Check queue assignment label
kubectl get pod <pod-name> -n zenml -o jsonpath='{.metadata.labels.kai\.scheduler/queue}'
# → default-queue

# Watch PodGroups (if gang scheduling is enabled)
kubectl get podgroups.scheduling.run.ai -n zenml -w

# See ZenML pipeline run metadata
zenml pipeline run list
```

---

## Project Structure

```
kai_scheduler_demo/
├── pipelines/
│   └── gpu_benchmark.py       # @pipeline connecting both steps
├── steps/
│   ├── cuda_matrix_benchmark.py  # CUDA matmul GFLOPS benchmark
│   └── pytorch_cnn_train.py      # Minimal CNN training
├── configs/
│   ├── kai_demo.yaml             # Full GPU + KAI-Scheduler config
│   ├── kai_demo_gpu_sharing.yaml # GPU time-slicing config
│   └── kai_demo_local.yaml       # CPU-only for local dev
├── k8s/
│   ├── queues.yaml               # KAI Queue CRDs (root + leaf queues)
│   └── priority-classes.yaml     # PriorityClass manifests
├── run.py                        # Click CLI entrypoint
├── requirements.txt
└── README.md
```
