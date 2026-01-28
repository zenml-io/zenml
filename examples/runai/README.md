# Run:AI Integration Example

This example demonstrates two powerful Run:AI integration patterns with ZenML:

1. **Step Operator** - Selectively offload GPU-intensive training steps to Run:AI
2. **Deployer** - Deploy inference pipelines as HTTP services on Run:AI with fractional GPU and autoscaling

## Overview

### Step Operator Pattern (Training)

Selectively offload only GPU-intensive steps to Run:AI while running other steps on a standard Kubernetes orchestrator:

- **Data Loader** - Runs on Kubernetes (CPU) - lightweight data preparation
- **GPU Trainer** - Offloaded to Run:AI with fractional GPU - PyTorch training

This is more cost-effective than running the entire pipeline on GPU nodes.

### Deployer Pattern (Inference)

Deploy inference pipelines as HTTP services on Run:AI with:

- **Fractional GPU** - Share GPUs across multiple inference workloads (e.g., 0.25 GPU per service)
- **Autoscaling** - Automatically scale replicas based on request load
- **HTTP API** - Access predictions via REST endpoints

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

#### Run:AI Step Operator (for GPU training steps)

```bash
zenml step-operator register runai \
    --flavor=runai \
    --client_id=<YOUR_CLIENT_ID> \
    --client_secret=<YOUR_CLIENT_SECRET> \
    --runai_base_url=https://<YOUR_ORG>.run.ai \
    --project_name=<YOUR_PROJECT>
```

#### Run:AI Deployer (for inference deployments)

```bash
zenml deployer register runai \
    --flavor=runai \
    --client_id=<YOUR_CLIENT_ID> \
    --client_secret=<YOUR_CLIENT_SECRET> \
    --runai_base_url=https://<YOUR_ORG>.run.ai \
    --project_name=<YOUR_PROJECT>
```

#### Other Required Components

```bash
# Kubernetes orchestrator (for CPU steps)
zenml orchestrator register k8s_orch \
    --flavor=kubernetes \
    --kubernetes_context=<YOUR_K8S_CONTEXT>

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
    -d runai \
    -a gcs_store \
    -c gcr_registry \
    -i local_builder \
    --set
```

## Running the Example

### Training with Step Operator

```bash
cd examples/runai/
python run.py --train
```

This runs the training pipeline where:
- `data_loader` runs on Kubernetes (CPU)
- `gpu_trainer` is offloaded to Run:AI (GPU)

### Deploying Inference Pipeline

#### Option 1: Using Python SDK

```bash
python run.py --deploy --deployment-name my-inference
```

#### Option 2: Using CLI

```bash
# Deploy the pipeline
zenml pipeline deploy pipelines.inference_pipeline --name my-inference

# Or deploy with a specific snapshot
zenml pipeline snapshot create inference_pipeline --name my-snapshot
zenml pipeline snapshot deploy my-snapshot --deployment my-inference
```

### Invoking Deployments

```bash
# Via CLI
zenml deployment invoke my-inference --features='[0.5, -0.3, 1.2, 0.8]'

# Via HTTP
curl -X POST <ENDPOINT_URL>/invoke \
    -H "Content-Type: application/json" \
    -d '{"parameters": {"features": [0.5, -0.3, 1.2, 0.8]}}'
```

### Managing Deployments

```bash
# List all deployments
zenml deployment list

# View deployment details
zenml deployment describe my-inference

# View deployment logs
zenml deployment logs my-inference

# Deprovision (stop but keep record)
zenml deployment deprovision my-inference

# Re-provision (restart)
zenml deployment provision my-inference

# Delete completely
zenml deployment delete my-inference
```

## Configuration Examples

### Step Operator Settings

```python
from zenml.integrations.runai.flavors import RunAIStepOperatorSettings

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

    # Metadata
    labels={"team": "ml-platform"},
)
```

### Deployer Settings

```python
from zenml.integrations.runai.flavors import RunAIDeployerSettings

@pipeline(settings={"deployer": RunAIDeployerSettings(
    # Fractional GPU for cost-effective inference
    gpu_portion_request=0.25,
    gpu_request_type="portion",

    # CPU resources
    cpu_core_request=1.0,
    cpu_memory_request="2Gi",

    # Autoscaling
    min_replicas=1,
    max_replicas=5,

    # Metadata
    labels={"app": "inference-service"},
)})
def my_inference_pipeline(input: str = "default") -> str:
    return process(input=input)
```

### GPU Allocation Examples

```python
# Quarter GPU (cost-effective inference)
RunAIDeployerSettings(gpu_portion_request=0.25)

# Half GPU
RunAIDeployerSettings(gpu_portion_request=0.5)

# Full GPU
RunAIDeployerSettings(gpu_portion_request=1.0)

# Memory-based allocation
RunAIDeployerSettings(
    gpu_memory_request="20Gi",
    gpu_request_type="memory",
)
```

## Pipeline Requirements for Deployment

### Input Parameters

All parameters must have default values for deployment:

```python
@pipeline
def inference_pipeline(
    features: List[float] = [0.0, 0.0, 0.0, 0.0]  # Default required
) -> Dict[str, float]:
    return predict(features=features)
```

### Return Values

Pipeline outputs must be JSON-serializable step outputs:

```python
from typing import Annotated

@step
def predict(features: List[float]) -> Annotated[Dict[str, float], "prediction"]:
    return {"probability": 0.85, "class": 1}

@pipeline
def inference_pipeline(features: List[float] = []) -> Dict[str, float]:
    return predict(features=features)
```

### Sample Response

```json
{
    "success": true,
    "outputs": {
        "prediction_result": {
            "prediction": 1.0,
            "probability": 0.85,
            "num_features": 4.0
        }
    },
    "execution_time": 0.234,
    "metadata": {
        "deployment_name": "my-inference",
        "parameters_used": {
            "features": [0.5, -0.3, 1.2, 0.8]
        }
    }
}
```

## Monitoring

### View Pipeline Status

```bash
zenml pipeline runs list
zenml pipeline runs describe <RUN_NAME>
```

### View Deployments

```bash
zenml deployment list
zenml deployment describe <DEPLOYMENT_NAME>
```

### View Run:AI Dashboard

1. Log in to your Run:AI control plane
2. Navigate to **Workloads > Training** (for step operator jobs)
3. Navigate to **Workloads > Inference** (for deployed services)
4. View logs, resource usage, and GPU metrics

## Troubleshooting

### Issue: "Step operator 'runai' not found"

**Solution**: Ensure the step operator is registered and the stack is active:
```bash
zenml step-operator list
zenml stack describe
```

### Issue: "No deployer configured in active stack"

**Solution**: Register and add a Run:AI deployer to your stack:
```bash
zenml deployer register runai --flavor=runai ...
zenml stack update -d runai
```

### Issue: "Project not found in Run:AI"

**Solution**: Verify the project name matches exactly in Run:AI control plane.

### Issue: "Insufficient GPU quota"

**Solution**:
1. Request more quota from your admin
2. Reduce `gpu_portion_request` (e.g., 0.25)
3. Wait for other workloads to complete

### Issue: Deployment not getting endpoint URL

**Solution**: Check Run:AI workload status in the UI. The endpoint URL is assigned once the workload reaches "Running" state.

### Issue: "Parameters must have default values"

**Solution**: All pipeline parameters must have default values for deployment:
```python
# Wrong
def my_pipeline(features: List[float]) -> ...:

# Correct
def my_pipeline(features: List[float] = []) -> ...:
```

## Resources

- [Run:AI Documentation](https://docs.run.ai/)
- [ZenML Deployment Guide](https://docs.zenml.io/concepts/deployment)
- [ZenML Step Operators Guide](https://docs.zenml.io/component-guide/step-operators)
- [ZenML Deployers Guide](https://docs.zenml.io/component-guide/deployers)
