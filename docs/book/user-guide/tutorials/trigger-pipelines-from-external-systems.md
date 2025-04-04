# Triggering Pipelines from External Systems

This tutorial demonstrates practical approaches to triggering ZenML pipelines from external systems. We'll explore multiple methods, from ZenML Pro's Run Templates to open-source alternatives using custom APIs, serverless functions, and GitHub Actions.

## Introduction: The Pipeline Triggering Challenge

In development environments, you typically run your ZenML pipelines directly from Python code. However, in production, pipelines often need to be triggered by external systems:

- Scheduled retraining of models based on a time interval
- Batch inference when new data arrives
- Event-driven ML workflows responding to data drift or performance degradation
- Integration with CI/CD pipelines and other automation systems
- Invocation from custom applications via API calls

Each scenario requires a reliable way to trigger the right version of your pipeline with the correct parameters, while maintaining security and operational standards.

{% hint style="info" %}
For our full reference documentation on pipeline triggering, see the [Trigger a Pipeline (Run Templates)](https://docs.zenml.io/how-to/trigger-pipelines) page.
{% endhint %}

## Prerequisites

Before starting this tutorial, make sure you have:

1. ZenML installed and configured
2. Basic understanding of [ZenML pipelines and steps](https://docs.zenml.io/getting-started/core-concepts)
3. A simple pipeline to use for triggering examples

## Creating a Sample Pipeline for External Triggering

First, let's create a basic pipeline that we'll use throughout this tutorial. This pipeline takes a dataset URL and model type as inputs, then performs a simple training operation:

```python
from typing import Dict, Any, Union
from zenml import pipeline, step
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

@step
def load_data(data_url: str) -> pd.DataFrame:
    """Load data from a URL (simulated for this example)."""
    # For demonstration, we'll create synthetic data
    np.random.seed(42)
    n_samples = 1000
    
    print(f"Loading data from: {data_url}")
    # In a real scenario, you'd load from data_url
    # E.g., pd.read_csv(data_url)
    
    data = pd.DataFrame({
        'feature_1': np.random.normal(0, 1, n_samples),
        'feature_2': np.random.normal(0, 1, n_samples),
        'feature_3': np.random.normal(0, 1, n_samples),
        'target': np.random.choice([0, 1], n_samples)
    })
    return data

@step
def preprocess(data: pd.DataFrame) -> Dict[str, Any]:
    """Split data into train and test sets."""
    X = data.drop('target', axis=1)
    y = data['target']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return {
        'X_train': X_train, 
        'X_test': X_test, 
        'y_train': y_train, 
        'y_test': y_test
    }

@step
def train_model(
    datasets: Dict[str, Any], 
    model_type: str = "random_forest"
) -> Union[RandomForestClassifier, GradientBoostingClassifier]:
    """Train a model based on the specified type."""
    X_train = datasets['X_train']
    y_train = datasets['y_train']
    
    if model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == "gradient_boosting":
        model = GradientBoostingClassifier(random_state=42)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    print(f"Training a {model_type} model...")
    model.fit(X_train, y_train)
    return model

@step
def evaluate(
    datasets: Dict[str, Any], 
    model: Union[RandomForestClassifier, GradientBoostingClassifier]
) -> Dict[str, float]:
    """Evaluate the model and return metrics."""
    X_test = datasets['X_test']
    y_test = datasets['y_test']
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model accuracy: {accuracy:.4f}")
    return {'accuracy': float(accuracy)}


@pipeline
def training_pipeline(
    data_url: str = "s3://example-bucket/data.csv",
    model_type: str = "random_forest"
):
    """A configurable training pipeline that can be triggered externally."""
    data = load_data(data_url)
    datasets = preprocess(data)
    model = train_model(datasets, model_type)
    metrics = evaluate(datasets, model)

# For local execution during development
if __name__ == "__main__":
    # Run with default parameters
    training_pipeline()
```

This pipeline is designed to be configurable with parameters that might change between runs:
- `data_url`: Where to find the input data
- `model_type`: Which algorithm to use

These parameters make it an ideal candidate for external triggering scenarios where we want to run the same pipeline with different configurations.

## Method 1: Using Run Templates (ZenML Pro)

{% hint style="success" %}
This is a [ZenML Pro](https://zenml.io/pro)-only feature. Please [sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

Run Templates are the most straightforward way to trigger pipelines externally in ZenML. They provide a pre-defined, parameterized configuration that can be executed via multiple interfaces.

### Creating a Run Template

First, we need to create a template based on our pipeline. This requires having a remote stack with at least a remote orchestrator, artifact store, and container registry.

#### Using Python:

```python
from zenml.client import Client

# First get the pipeline by name
pipeline = Client().get_pipeline("training_pipeline")

# Get the most recent runs for this pipeline
runs = Client().list_pipeline_runs(
    pipeline_id=pipeline.id, 
    sort_by="desc:created", 
    size=1
)

if runs:
    # Use the most recent run
    latest_run = runs[0]
    
    # Create a template from this run
    template = Client().create_run_template(
        name="production-training-template", 
        deployment_id=latest_run.deployment_id
    )
    
    print(f"Created template: {template.name} with ID: {template.id}")
```

#### Using CLI:

```bash
# The source path is the module path to your pipeline
zenml pipeline create-run-template training_pipeline \
    --name=production-training-template
```

### Triggering a Template

Once you have created a template, there are multiple ways to trigger it, either programmatically with the Python client or via REST API for external systems.

#### Using the Python Client:

```python
from zenml.client import Client

# Find templates for a specific pipeline
pipeline = Client().get_pipeline("training_pipeline")
templates = Client().list_run_templates()
templates = [t for t in templates if t.pipeline.id == pipeline.id]

if templates:
    # Use the first matching template
    template = templates[0]
    print(f"Using template: {template.name} (ID: {template.id})")
    
    # Get the template's configuration
    config = template.config_template
    
    # Update the configuration with step parameters
    # Note: Parameters must be set at the step level rather than pipeline level
    config["steps"] = {
        "load_data": {
            "parameters": {
                "data_url": "s3://test-bucket/latest-data.csv",
            }
        },
        "train_model": {
            "parameters": {
                "model_type": "gradient_boosting",
            }
        }
    }
    
    # Trigger the pipeline with the updated configuration
    run = Client().trigger_pipeline(
        template_id=template.id,
        run_configuration=config,
    )
    
    print(f"Triggered pipeline run with ID: {run.id}")
```

#### Using the REST API:

The REST API is ideal for external system integration, allowing you to trigger pipelines from non-Python environments:

```bash
# Step 1: Get the pipeline ID
curl -X 'GET' \
  'https://<YOUR_ZENML_SERVER>/api/v1/pipelines?name=training_pipeline' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'

# Step 2: Get the template ID using the pipeline_id
curl -X 'GET' \
  'https://<YOUR_ZENML_SERVER>/api/v1/run_templates?pipeline_id=<PIPELINE_ID>' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'

# Step 3: Trigger the pipeline with custom parameters
curl -X 'POST' \
  'https://<YOUR_ZENML_SERVER>/api/v1/run_templates/<TEMPLATE_ID>/runs' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>' \
  -d '{
    "steps": {
      "load_data": {
        "parameters": {
          "data_url": "s3://production-bucket/latest-data.csv"
        }
      },
      "train_model": {
        "parameters": {
          "model_type": "gradient_boosting"
        }
      }
    }
  }'
```

> Note: When using the REST API, you need to specify parameters at the step level, not at the pipeline level. This matches how parameters are configured in the Python client.

### Security Considerations for API Tokens

When using the REST API for external systems, proper token management is critical:

```python
from zenml.client import Client

# Create a service account for automated triggers
service_account = Client().create_service_account(
    name="pipeline-trigger-service",
    description="Service account for external pipeline triggering"
)

# Generate API token with appropriate permissions
token = Client().create_service_account_token(
    service_account.id,
    name="production-trigger-token",
    description="Token for production pipeline triggers"
)

print(f"Store this token securely: {token.token}")
# Make sure to save this token value securely
```

Use this token in your API calls, and store it securely in your external system (e.g., as a GitHub Secret, AWS Secret, or environment variable).

## Method 2: Building a Custom Trigger API (Open Source)

If you're using the open-source version of ZenML or prefer a customized solution, you can create your own API wrapper around pipeline execution. This API can support both direct pipeline execution and run template triggering.

### Creating a FastAPI Wrapper

Create a file called `pipeline_api.py`:

```python
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os
import sys
from typing import Dict, Any, Optional
from uuid import UUID
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration

# Setup FastAPI app
app = FastAPI(title="ZenML Pipeline Trigger API")

# Simple API key authentication
API_KEY = os.environ.get("PIPELINE_API_KEY", "your-secure-api-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Request models for parameters
class StepParameter(BaseModel):
    parameters: Dict[str, Any]

class PipelineRequest(BaseModel):
    pipeline_name: str
    steps: Dict[str, StepParameter]
    config_path: Optional[str] = None

class TemplateRunRequest(BaseModel):
    template_id: UUID
    steps: Dict[str, StepParameter] = {}

@app.post("/trigger")
async def trigger_pipeline(
    request: PipelineRequest, 
    api_key: str = Depends(get_api_key)
):
    """Trigger a ZenML pipeline with the given parameters."""
    try:
        # Dynamically import the pipeline
        pipeline_func = import_pipeline(request.pipeline_name)
        
        # Configure the pipeline
        if request.config_path:
            configured_pipeline = pipeline_func.with_options(config_path=request.config_path)
        else:
            configured_pipeline = pipeline_func
        
        # Extract parameters from steps
        step_parameters = {}
        for step_name, step_config in request.steps.items():
            if step_config.parameters:
                step_parameters.update(step_config.parameters)
        
        # Run the pipeline with the provided parameters
        run = configured_pipeline(**step_parameters)
        
        return {
            "status": "success", 
            "message": f"Pipeline '{request.pipeline_name}' triggered successfully",
            "run_id": run.id if hasattr(run, 'id') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger pipeline: {str(e)}")

@app.post("/trigger-template")
async def trigger_template(
    request: TemplateRunRequest,
    api_key: str = Depends(get_api_key)
):
    """Trigger a pipeline using a run template."""
    try:
        # Get the template
        template = Client().get_run_template(request.template_id)
        
        # Get the template's configuration
        config = template.config_template or {}
        
        # Update the configuration with step parameters
        config["steps"] = {
            step_name: {"parameters": step_config.parameters}
            for step_name, step_config in request.steps.items()
        }
        
        # Trigger the pipeline with the updated configuration
        run = Client().trigger_pipeline(
            template_id=template.id,
            run_configuration=PipelineRunConfiguration(**config),
        )
        
        return {
            "status": "success",
            "message": f"Pipeline triggered successfully from template '{template.name}'",
            "run_id": run.id,
            "template_id": template.id,
            "template_name": template.name
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger template: {str(e)}"
        )
```

### Deploying Your Custom API

Deploy the API service to make it accessible to external systems:

```bash
# Install required dependencies
pip install fastapi uvicorn

# Set a secure API key
export PIPELINE_API_KEY="your-secure-api-key-here"

# Start the API server
python pipeline_api.py
```

For production, consider deploying as a containerized service:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install ZenML and other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PIPELINE_API_KEY=${PIPELINE_API_KEY}

# Expose the port
EXPOSE 8000

# Run the API
CMD ["python", "pipeline_api.py"]
```

### Triggering Your Pipeline via the Custom API

You can trigger pipelines in two ways through the custom API:

#### 1. Direct Pipeline Execution

This method runs the pipeline directly with the specified parameters:

```bash
curl -X 'POST' \
  'http://your-api-server:8000/trigger' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-secure-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{
    "pipeline_name": "training_pipeline",
    "steps": {
      "load_data": {
        "parameters": {
          "data_url": "s3://some-bucket/new-data.csv"
        }
      },
      "train_model": {
        "parameters": {
          "model_type": "gradient_boosting"
        }
      }
    }
  }'
```

#### 2. Run Template Execution

This method uses a pre-configured run template, which is ideal for production scenarios:

```bash
curl -X 'POST' \
  'http://your-api-server:8000/trigger-template' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-secure-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{
    "template_id": "YOUR_TEMPLATE_ID",
    "steps": {
      "load_data": {
        "parameters": {
          "data_url": "s3://some-bucket/new-data.csv"
        }
      },
      "train_model": {
        "parameters": {
          "model_type": "gradient_boosting"
        }
      }
    }
  }'
```

The template-based approach offers several advantages:
- Consistent pipeline configuration across runs
- Pre-configured stack and environment settings
- Centralized management of pipeline versions
- Better control over production deployments

## Best Practices & Troubleshooting

### Security Best Practices

1. **API Keys**: Always use API keys or tokens for authentication
2. **Principle of Least Privilege**: Grant only necessary permissions to service accounts
3. **Key Rotation**: Rotate API keys regularly
4. **Secure Storage**: Store credentials in secure locations (not in code)
5. **TLS**: Use HTTPS for all API endpoints

### Monitoring and Observability

Implement monitoring for your trigger mechanisms:

```python
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline-trigger")

def log_trigger_attempt(pipeline_name, parameters, source):
    """Log pipeline trigger attempts."""
    timestamp = datetime.now().isoformat()
    logger.info(f"TRIGGER_ATTEMPT|{timestamp}|{pipeline_name}|{source}|{parameters}")

def log_trigger_success(pipeline_name, run_id, source):
    """Log successful pipeline triggers."""
    timestamp = datetime.now().isoformat()
    logger.info(f"TRIGGER_SUCCESS|{timestamp}|{pipeline_name}|{source}|{run_id}")

def log_trigger_failure(pipeline_name, error, source):
    """Log failed pipeline triggers."""
    timestamp = datetime.now().isoformat()
    logger.error(f"TRIGGER_FAILURE|{timestamp}|{pipeline_name}|{source}|{error}")

# Use in your trigger code
try:
    log_trigger_attempt("training_pipeline", parameters, "rest_api")
    run = Client().trigger_pipeline(
        pipeline_name_or_id="training_pipeline",
        run_configuration=run_config
    )
    log_trigger_success("training_pipeline", run.id, "rest_api")
except Exception as e:
    log_trigger_failure("training_pipeline", str(e), "rest_api")
    raise
```

## Conclusion: Choosing the Right Approach

The best approach for triggering pipelines depends on your specific needs:

1. **ZenML Pro Run Templates**: Ideal for teams that need a complete, managed solution with UI support and centralized management

2. **Custom API**: Best for teams that need full control over the triggering mechanism and want to embed it within their own infrastructure

Regardless of your approach, always prioritize:
- Security (authentication and authorization)
- Reliability (error handling and retries)
- Observability (logging and monitoring)

## Next Steps

Now that you understand how to trigger ZenML pipelines from external systems, consider exploring:

1. [Managing scheduled pipelines](managing-scheduled-pipelines.md) for time-based execution
2. Implementing [comprehensive CI/CD](https://docs.zenml.io/user-guides/production-guide/ci-cd) for your ML workflows
3. Setting up [monitoring and alerting](https://docs.zenml.io/stacks/alerters) for pipeline failures
