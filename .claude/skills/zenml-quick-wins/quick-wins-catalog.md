# ZenML Quick Wins Catalog

Detailed implementation guides for each quick win. Each section is self-contained.

---

## 1. Metadata Logging

**Why:** Foundation for reproducibility, analytics, and experiment comparison. Everything else builds on this.

### Basic Implementation

```python
from zenml import step, log_metadata

@step
def train_model(data, learning_rate: float = 1e-3, epochs: int = 10):
    # Your training code
    model = train(data, lr=learning_rate, epochs=epochs)
    metrics = evaluate(model, data)
    
    # Log training parameters and results
    log_metadata({
        "learning_rate": learning_rate,
        "epochs": epochs,
        "accuracy": metrics["accuracy"],
        "loss": metrics["loss"],
    })
    return model
```

### Grouped Metadata (Better Organization)

```python
log_metadata({
    "training_params": {
        "learning_rate": 1e-3,
        "epochs": 10,
        "batch_size": 32
    },
    "metrics": {
        "accuracy": 0.95,
        "f1_score": 0.93,
        "loss": 0.05
    },
    "dataset_info": {
        "num_samples": 10000,
        "features": ["age", "income", "score"]
    }
})
```

### Special Metadata Types

```python
from zenml.metadata.metadata_types import StorageSize, Uri

log_metadata({
    "dataset_source": Uri("gs://my-bucket/data.csv"),
    "model_size": StorageSize(256000000),  # bytes
})
```

### Logging to Different Entities

```python
# To artifact (from within step)
log_metadata({"schema_version": "v2"}, infer_artifact=True)

# To model (from within step in model-linked pipeline)
log_metadata({"accuracy": 0.95}, infer_model=True)

# To specific artifact (outside step)
from zenml.client import Client
Client().update_artifact(artifact_id, metadata={"key": "value"})
```

**Docs:** https://docs.zenml.io/concepts/metadata

---

## 2. Experiment Comparison (ZenML Pro)

**Why:** Visual comparison of runs with parallel coordinate plots. Requires metadata (#1).

### Setup

No code changes needed. Once metadata is logged:
1. Open ZenML Dashboard
2. Navigate to **Compare** view
3. Select runs to compare
4. Use table view or parallel coordinates plot

### Best Practices

- Use consistent metadata keys across runs
- Log numerical values for plot compatibility
- Include hyperparameters AND metrics

**Docs:** https://www.zenml.io/blog/new-dashboard-feature-compare-your-experiments

---

## 3. Autologging (Experiment Trackers)

**Why:** Automatic metric/artifact tracking without modifying step code.

### MLflow Setup

```bash
zenml integration install mlflow -y
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml stack update <stack_name> -e mlflow_tracker
```

```python
from zenml import step
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker

@step(experiment_tracker=experiment_tracker.name)
def train_model(data):
    # MLflow autologging captures:
    # - Parameters, metrics, model artifacts
    # - Framework-specific data (sklearn, pytorch, etc.)
    model = train_sklearn_model(data)
    return model
```

### Weights & Biases Setup

```bash
zenml integration install wandb -y
zenml secret create wandb --api_key=$WANDB_API_KEY
zenml experiment-tracker register wandb_tracker \
    --flavor=wandb \
    --api_key={{wandb.api_key}} \
    --project_name=my_project
zenml stack update <stack_name> -e wandb_tracker
```

### Framework Support

| Tracker | Auto-logged Frameworks |
|---------|----------------------|
| MLflow | sklearn, pytorch, tensorflow, xgboost, lightgbm, spark |
| W&B | Most ML frameworks + media artifacts |
| Neptune | Manual logging, auto hardware metrics |
| Comet | Most frameworks + source code |

**Docs:** https://docs.zenml.io/stacks/stack-components/experiment-trackers

---

## 4. Alerts (Slack/Discord)

**Why:** Instant notifications without checking dashboards.

### Slack Setup

```bash
zenml integration install slack -y

# Store the token securely (recommended)
zenml secret create slack_credentials --token=$SLACK_BOT_TOKEN

# Register alerter using secret reference
zenml alerter register slack_alerter \
    --flavor=slack \
    --slack_token={{slack_credentials.token}} \
    --default_slack_channel_id=<CHANNEL_ID>
zenml stack update <stack_name> -al slack_alerter
```

### Usage in Pipeline

```python
from zenml.integrations.slack.steps import slack_alerter_post_step

@pipeline
def training_pipeline():
    model = train_step()
    metrics = evaluate_step(model)
    
    # Send notification on completion
    slack_alerter_post_step(
        message=f"Training complete! Accuracy: {metrics['accuracy']:.2%}"
    )
```

### Discord Setup

```bash
zenml integration install discord -y

# Store the token securely (recommended)
zenml secret create discord_credentials --token=$DISCORD_BOT_TOKEN

# Register alerter using secret reference
zenml alerter register discord_alerter \
    --flavor=discord \
    --discord_token={{discord_credentials.token}} \
    --default_discord_channel_id=<CHANNEL_ID>
```

### Human-in-the-Loop Approval

```python
from zenml.integrations.slack.steps import slack_alerter_ask_step

@pipeline
def deployment_pipeline():
    model = train_step()
    
    # Wait for approval before deploying
    approved = slack_alerter_ask_step(
        message="Deploy model to production?",
        approve_message_regex="yes|approve|👍",
        disapprove_message_regex="no|reject|👎"
    )
    
    deploy_step(model, approved=approved)
```

**Docs:** https://docs.zenml.io/stacks/stack-components/alerters/slack

---

## 5. Cron Scheduling

**Why:** Automate recurring pipeline runs.

### Basic Schedule

```python
from zenml.config.schedule import Schedule
from zenml import pipeline

schedule = Schedule(
    name="daily-training",
    cron_expression="0 3 * * *"  # 3 AM daily
)

@pipeline
def training_pipeline():
    ...

# Attach and run once to register
training_pipeline.with_options(schedule=schedule)()
```

### Common Cron Expressions

| Expression | Schedule |
|------------|----------|
| `0 3 * * *` | Daily at 3 AM |
| `0 0 * * 0` | Weekly on Sunday |
| `0 0 1 * *` | Monthly on 1st |
| `*/30 * * * *` | Every 30 minutes |
| `0 9-17 * * 1-5` | Hourly 9-5 weekdays |

### Schedule with Time Bounds

```python
from datetime import datetime

schedule = Schedule(
    name="limited-schedule",
    cron_expression="0 3 * * *",
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31)
)
```

### Managing Schedules

```bash
# List schedules
zenml pipeline schedules list

# Delete a schedule (also delete in orchestrator!)
zenml pipeline schedules delete <schedule_id>
```

**Important:** Deleting from ZenML doesn't remove from orchestrator. Delete in both places.

**Docs:** https://docs.zenml.io/how-to/steps-pipelines/scheduling

---

## 6. Warm Pools / Persistent Resources

**Why:** Eliminate cold-start delays (minutes → seconds).

### SageMaker Warm Pools

```bash
zenml orchestrator register sagemaker_warm \
    --flavor=sagemaker \
    --use_warm_pools=True

zenml stack update <stack_name> -o sagemaker_warm
```

### Vertex AI Persistent Resources

```bash
zenml step-operator register vertex_persistent \
    --flavor=vertex \
    --persistent_resource_id=my-resource-id

zenml stack update <stack_name> -s vertex_persistent
```

**Note:** Warm pools incur charges when idle. Set appropriate timeouts.

**Docs:** https://docs.zenml.io/stacks/stack-components/orchestrators/sagemaker

---

## 7. Secrets Management

**Why:** Keep credentials out of code.

### Create Secrets

```bash
# Single value
zenml secret create wandb --api_key=$WANDB_API_KEY

# Multiple values
zenml secret create database \
    --username=db_user \
    --password=db_pass \
    --host=db.example.com
```

### Reference in Stack Components

```bash
zenml experiment-tracker register wandb_tracker \
    --flavor=wandb \
    --api_key={{wandb.api_key}}
```

### Access in Code

```python
from zenml.client import Client

client = Client()
secret = client.get_secret("database")
username = secret.secret_values["username"]
password = secret.secret_values["password"]
```

### Manage Secrets

```bash
zenml secret list
zenml secret get <name>
zenml secret update <name> --key=new_value
zenml secret delete <name>
```

**Docs:** https://docs.zenml.io/concepts/secrets

---

## 8. Local Smoke Tests

**Why:** Fast iteration with Docker before cloud deployment.

### Setup Smoke Test Stack

```bash
zenml orchestrator register local_docker_orch --flavor=local_docker
zenml stack register smoke_test_stack \
    -o local_docker_orch \
    -a <your_artifact_store>
```

### Parameterized Pipeline for Testing

```python
@pipeline
def training_pipeline(sample_fraction: float = 1.0, epochs: int = 100):
    data = load_data_step(sample_fraction=sample_fraction)
    model = train_step(data, epochs=epochs)
    evaluate_step(model, data)

# Smoke test: small data, few epochs
# zenml stack set smoke_test_stack
training_pipeline(sample_fraction=0.01, epochs=2)

# Production: full data
# zenml stack set production_stack
training_pipeline(sample_fraction=1.0, epochs=100)
```

### Pattern: Environment-Aware Defaults

```python
import os

SMOKE_TEST = os.getenv("ZENML_SMOKE_TEST", "false").lower() == "true"

@pipeline
def training_pipeline(
    sample_fraction: float = 0.01 if SMOKE_TEST else 1.0,
    epochs: int = 2 if SMOKE_TEST else 100
):
    ...
```

**Docs:** https://docs.zenml.io/stacks/stack-components/orchestrators/local-docker

---

## 9. Tags

**Why:** Organize and filter ML assets.

### Tag Pipelines

```python
from zenml import pipeline, Tag

@pipeline(tags=["fraud-detection", "training", "v2"])
def training_pipeline():
    ...

# Exclusive tag (only one can have it)
@pipeline(tags=[Tag(name="production", exclusive=True)])
def prod_pipeline():
    ...

# Cascade tags to artifacts
@pipeline(tags=[Tag(name="experiment-12", cascade=True)])
def experiment_pipeline():
    # All artifacts get "experiment-12" tag
    ...
```

### Tag Programmatically

```python
from zenml import step, add_tags

@step
def evaluate_step(accuracy: float):
    if accuracy > 0.9:
        add_tags(tags=["high-accuracy"], infer_artifact=True)
    return accuracy
```

### Query by Tags

```python
from zenml.client import Client

# Find production models
Client().list_models(tags=["production"])

# Prefix/contains filtering
Client().list_runs(tags=["startswith:experiment-"])
Client().list_artifacts(tags=["contains:valid"])
```

### CLI Tag Operations

```bash
# Add tags to existing run
zenml pipeline runs tag <run_id> --tag="reviewed"

# Remove tags
zenml pipeline runs untag <run_id> --tag="test"
```

**Docs:** https://docs.zenml.io/concepts/tags

---

## 10. Git Repository Hooks

**Why:** Automatic code versioning and faster Docker builds.

### Setup

```bash
zenml integration install github  # or gitlab

# Create token secret first (recommended)
zenml secret create github_secret --token=$GITHUB_TOKEN

# Register code repository using secret reference
zenml code-repository register project_repo \
    --type=github \
    --url=https://github.com/your/repo.git \
    --token={{github_secret.token}}
```

### What You Get

- Every run tracks exact commit SHA
- Dirty repo detection (uncommitted changes flagged)
- Docker builds download from repo (faster, cached)
- Shared builds across team

### GitLab Setup

```bash
zenml integration install gitlab

# Create token secret first
zenml secret create gitlab_secret --token=$GITLAB_TOKEN

# Register code repository using secret reference
zenml code-repository register project_repo \
    --type=gitlab \
    --url=https://gitlab.com/your/repo.git \
    --token={{gitlab_secret.token}}
```

**Docs:** https://docs.zenml.io/user-guides/production-guide/connect-code-repository

---

## 11. HTML Reports

**Why:** Beautiful visualizations in dashboard.

### Basic Report

```python
from zenml import step
from zenml.types import HTMLString

@step
def generate_report(metrics: dict) -> HTMLString:
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            .metric {{ margin: 10px 0; }}
            .value {{ font-size: 24px; color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>Training Report</h1>
        <div class="metric">
            <div>Accuracy</div>
            <div class="value">{metrics['accuracy']:.2%}</div>
        </div>
        <div class="metric">
            <div>Loss</div>
            <div class="value">{metrics['loss']:.4f}</div>
        </div>
    </body>
    </html>
    """
    return HTMLString(html)
```

### With Charts (Chart.js)

```python
@step
def chart_report(history: list) -> HTMLString:
    data_json = json.dumps(history)
    html = f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <canvas id="chart"></canvas>
        <script>
            const data = {data_json};
            new Chart(document.getElementById('chart'), {{
                type: 'line',
                data: {{
                    labels: data.map((_, i) => i),
                    datasets: [{{ label: 'Loss', data: data }}]
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLString(html)
```

**Docs:** https://docs.zenml.io/concepts/artifacts/visualizations

---

## 12. Model Control Plane

**Why:** Central hub for model lineage, governance, and lifecycle.

### Register a Model

```python
from zenml import pipeline, Model

model = Model(
    name="fraud_classifier",
    description="Fraud detection model",
    tags=["classification", "financial"]
)

@pipeline(model=model)
def training_pipeline():
    data = load_data_step()
    model = train_step(data)
    evaluate_step(model)
```

### Log Metrics to Model

```python
from zenml import step, log_metadata

@step
def evaluate_step(model, test_data):
    accuracy = evaluate(model, test_data)
    
    # Automatically attaches to pipeline's model
    log_metadata({"accuracy": accuracy}, infer_model=True)
    
    return accuracy
```

### Promote Model Stages

```python
from zenml import Model

# Get model and promote
model = Model(name="fraud_classifier", version="v3")
model.set_stage(stage="production", force=True)
```

### Query Models

```python
from zenml.client import Client

# List all versions
versions = Client().list_model_versions("fraud_classifier")

# Get specific version
model_v2 = Client().get_model_version("fraud_classifier", "v2")

# Compare versions
print(f"v1 accuracy: {model_v1.run_metadata['accuracy'].value}")
print(f"v2 accuracy: {model_v2.run_metadata['accuracy'].value}")
```

### CLI Operations

```bash
zenml model list
zenml model version list <model_name>
zenml model version update <model_name> <version> --stage=production
```

**Docs:** https://docs.zenml.io/concepts/models

---

## 13. Parent Docker Images

**Why:** Faster builds by pre-installing heavy dependencies.

### Create Parent Dockerfile

```dockerfile
# Dockerfile.parent
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential && rm -rf /var/lib/apt/lists/*

# Pre-install heavy dependencies
RUN pip install --no-cache-dir \
    zenml==0.70.0 \
    torch==2.0.0 \
    scikit-learn==1.2.2 \
    pandas==2.0.0

WORKDIR /app
```

### Build and Push

```bash
# Export stack requirements
zenml stack export-requirements --output-file stack_reqs.txt

# Build
docker build -t your-registry.io/zenml-parent:latest -f Dockerfile.parent .
docker push your-registry.io/zenml-parent:latest
```

### Use in Pipeline

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    parent_image="your-registry.io/zenml-parent:latest",
    requirements=["your-custom-package==1.0.0"]  # Only project-specific
)

@pipeline(settings={"docker": docker_settings})
def training_pipeline():
    ...
```

**Docs:** https://docs.zenml.io/concepts/containerization

---

## 14. ZenML Docs MCP Server

**Why:** IDE AI assistance grounded in live documentation.

### Claude Code Setup

```bash
claude mcp add zenmldocs --transport http https://docs.zenml.io/~gitbook/mcp
```

### Cursor Setup

Add to MCP settings JSON:

```json
{
  "mcpServers": {
    "zenmldocs": {
      "transport": {
        "type": "http",
        "url": "https://docs.zenml.io/~gitbook/mcp"
      }
    }
  }
}
```

### Usage

Prompt your IDE assistant:
> "Using the zenmldocs MCP server, show me how to register an MLflow experiment tracker."

**Benefits:**
- Live answers from current docs
- Fewer hallucinations with source grounding
- No context switching to browser

**Note:** Indexes released docs, not develop branch.

**Docs:** https://docs.zenml.io/reference/llms-txt

---

## 15. CLI Export Formats

**Why:** Machine-readable output for scripting and automation.

### Available Formats

```bash
# JSON (best for programmatic use)
zenml stack list --output=json

# YAML (config-friendly)
zenml pipeline list --output=yaml

# CSV/TSV (spreadsheets, data analysis)
zenml pipeline runs list --output=csv > runs.csv

# Filter columns
zenml stack list --columns=id,name,orchestrator --output=json
```

### Scripting Examples

```bash
# Find production stack ID
PROD_STACK=$(zenml stack list --output=json | jq -r '.items[] | select(.name=="production") | .id')

# Export recent runs for analysis
zenml pipeline runs list --size=100 --output=csv > analysis.csv

# Get all model names
zenml model list --output=json | jq -r '.items[].name'
```

### Environment Defaults

```bash
# Set default format
export ZENML_DEFAULT_OUTPUT=json

# Control column width
export ZENML_CLI_COLUMN_WIDTH=120
```

**Docs:** https://docs.zenml.io/reference/environment-variables

---

## Implementation Checklist Template

Use this for each quick win:

```markdown
## Quick Win #X: [Name]

### Prerequisites
- [ ] Prerequisite 1
- [ ] Prerequisite 2

### Implementation Steps
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

### Verification
- [ ] Test locally
- [ ] Verify in dashboard
- [ ] Document changes

### Notes
- Any issues encountered
- Customizations made
```
