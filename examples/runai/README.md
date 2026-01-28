# Run:AI Step Operator Example

This example demonstrates the **step operator pattern** with Run:AI - selectively offloading only GPU-intensive steps to Run:AI while running other steps on a standard Kubernetes orchestrator.

## Overview

This pipeline showcases selective GPU offloading:

1. **Data Loader** - Runs on Kubernetes (CPU) - lightweight data preparation
2. **GPU Trainer** - Offloaded to Run:AI with fractional GPU - PyTorch training

The key pattern: only steps that need GPU resources are offloaded to Run:AI, while CPU-only steps run on the regular orchestrator. This is more cost-effective than running the entire pipeline on GPU nodes.

## Step Operator Settings Showcase

The `gpu_trainer` step demonstrates various Run:AI settings:

```python
RunAIStepOperatorSettings(
    # Fractional GPU allocation
    gpu_portion_request=0.5,
    gpu_request_type="portion",

    # CPU resources with burst capability
    cpu_core_request=2.0,
    cpu_core_limit=4.0,
    cpu_memory_request="4Gi",
    cpu_memory_limit="8Gi",

    # Scheduling preferences
    preemptibility="preemptible",
    priority_class="train",

    # PyTorch DataLoader compatibility
    large_shm_request=True,

    # Execution control
    backoff_limit=2,
    termination_grace_period_seconds=60,

    # Metadata for tracking
    labels={"team": "ml-platform", "framework": "pytorch"},
    annotations={"zenml.io/example": "runai-step-operator"},

    # Environment variables
    environment_variables={"PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512"},
)
```

## Prerequisites

### 1. Run:AI Cluster Access

You need:
- Access to a Run:AI cluster (SaaS or self-hosted)
- Run:AI client credentials (client ID and secret)
- A Run:AI project with sufficient GPU quota

### 2. Get Run:AI Credentials

1. Log in to your Run:AI control plane
2. Navigate to **Settings > Applications**
3. Create a new application or use an existing one
4. Note down the **Client ID** and **Client Secret**

### 3. Install ZenML with Run:AI Integration

```bash
pip install "zenml[runai]"
zenml init
```

## Setup

### Step 1: Register Required Stack Components

#### Kubernetes Orchestrator (for CPU steps)

```bash
zenml orchestrator register k8s_orch \
    --flavor=kubernetes \
    --kubernetes_context=<YOUR_K8S_CONTEXT>
```

#### Run:AI Step Operator (for GPU steps)

```bash
zenml step-operator register runai \
    --flavor=runai \
    --client_id=id \
    --client_secret=secret \
    --runai_base_url=url\
    --project_name=project
```

#### Other Required Components

```bash
# Artifact store (GCS example)
zenml artifact-store register gcs_store \
    --flavor=gcp \
    --path=gs://your-bucket/zenml-artifacts

# Container registry (GCR example)
zenml container-registry register gcr_registry \
    --flavor=gcp \
    --uri=gcr.io/<PROJECT_ID>

# Image builder
zenml image-builder register local_builder \
    --flavor=local
```

### Step 2: Register and Activate the Stack

```bash
zenml stack register runai_stack \
    -o k8s_orch \
    -s runai \
    -a gcs_store \
    -c gcr_registry \
    -i local_builder \
    --set
```

## Running the Example

```bash
cd examples/runai/
python run.py
```

### Expected Output

1. **Data Loader** (runs on Kubernetes):
   ```
   Generating synthetic data...
     Total samples: 1000
     Features: 20
   Data loaded successfully
   ```

2. **GPU Trainer** (runs on Run:AI):
   ```
   Starting GPU training step...
   Using device: cuda
   GPU: NVIDIA A100-SXM4-40GB
   Training for 100 epochs...
   Epoch 25/100, Loss: 0.4521
   Epoch 50/100, Loss: 0.3012
   Epoch 75/100, Loss: 0.2234
   Epoch 100/100, Loss: 0.1856
   Training complete! Accuracy: 92.50%
   ```

## Customizing GPU Allocation

### Fractional GPU Examples

```python
# Quarter GPU
RunAIStepOperatorSettings(
    gpu_portion_request=0.25,
    gpu_request_type="portion",
)

# Full GPU
RunAIStepOperatorSettings(
    gpu_portion_request=1.0,
    gpu_request_type="portion",
)

# Multiple whole GPUs
RunAIStepOperatorSettings(
    gpu_devices_request=2,
    gpu_request_type="device",
)

# Memory-based allocation
RunAIStepOperatorSettings(
    gpu_memory_request="20Gi",
    gpu_request_type="memory",
)
```

### CPU-Only Steps

Steps without `step_operator="runai"` run on the Kubernetes orchestrator without GPU access. This is the default for the `data_loader` step.

## Monitoring

### View Pipeline Status

```bash
zenml pipeline runs list
zenml pipeline runs describe <RUN_NAME>
```

### View Run:AI Dashboard

1. Log in to your Run:AI control plane
2. Navigate to **Workloads > Training**
3. Find your workload (labeled with `framework: pytorch`)
4. View logs, resource usage, and GPU metrics

## Troubleshooting

### Issue: "Step operator 'runai' not found"

**Solution**: Ensure the step operator is registered and the stack is active:
```bash
zenml step-operator list
zenml stack describe
```

### Issue: "Project not found in Run:AI"

**Solution**: Verify the project name matches exactly in Run:AI control plane.

### Issue: "Insufficient GPU quota"

**Solution**:
1. Request more quota from your admin
2. Reduce `gpu_portion_request` (e.g., 0.25)
3. Wait for other workloads to complete

### Issue: GPU not available in step

**Solution**: Ensure your Run:AI project has real GPU nodes (not fake GPUs) and sufficient quota.

### Issue: PyTorch DataLoader fails with shared memory error

**Solution**: The example already sets `large_shm_request=True`. If using custom code with `num_workers > 0`, ensure this setting is enabled.

## Resources

- [Run:AI Documentation](https://docs.run.ai/)
- [ZenML Step Operators Guide](https://docs.zenml.io/component-guide/step-operators)
- [ZenML Run:AI Integration](https://docs.zenml.io/component-guide/step-operators/runai)
