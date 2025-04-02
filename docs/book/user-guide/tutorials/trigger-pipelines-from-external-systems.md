---
description: A step-by-step tutorial on how to reliably trigger ML pipelines from external systems using various methods
---

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

If you're using the open-source version of ZenML or prefer a customized solution, you can create your own API wrapper around pipeline execution.

### Creating a FastAPI Wrapper

Create a file called `pipeline_api.py`:

```python
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os
import sys
import importlib.util
from typing import Dict, Any, Optional

# Setup FastAPI app
app = FastAPI(title="ZenML Pipeline Trigger API")

# Simple API key authentication
API_KEY = os.environ.get("PIPELINE_API_KEY", "your-secure-api-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Request model for pipeline parameters
class PipelineRequest(BaseModel):
    pipeline_name: str
    parameters: Dict[str, Any]
    config_path: Optional[str] = None

# Import a pipeline dynamically
def import_pipeline(pipeline_name):
    """Import a pipeline function from available modules."""
    # This is a simplified example - in production you should limit which
    # modules can be imported for security reasons
    
    # For this example, assume pipelines are in the 'pipelines' module
    try:
        spec = importlib.util.find_spec(f"pipelines")
        if spec is None:
            raise ImportError(f"Module 'pipelines' not found")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the pipeline function
        if not hasattr(module, pipeline_name):
            raise AttributeError(f"Pipeline '{pipeline_name}' not found in module")
        
        return getattr(module, pipeline_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {str(e)}")

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
        
        # Run the pipeline with the provided parameters
        run = configured_pipeline(**request.parameters)
        
        return {
            "status": "success", 
            "message": f"Pipeline '{request.pipeline_name}' triggered successfully",
            "run_id": run.id if hasattr(run, 'id') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger pipeline: {str(e)}")

# Run the API server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
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

Now you can trigger your pipeline from any system that can make HTTP requests:

```bash
curl -X 'POST' \
  'http://your-api-server:8000/trigger' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-secure-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{
    "pipeline_name": "training_pipeline",
    "parameters": {
      "data_url": "s3://some-bucket/new-data.csv",
      "model_type": "gradient_boosting"
    }
  }'
```

## Method 3: Leveraging Serverless Functions

Cloud functions provide a serverless way to trigger pipelines without maintaining a dedicated API service.

### AWS Lambda Implementation

Create a file called `lambda_function.py`:

```python
import os
import sys
import json
import importlib.util
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import your ZenML pipeline module
sys.path.append('/opt')  # Layer with ZenML and dependencies

def import_pipeline(pipeline_name):
    """Import a pipeline function from available modules."""
    try:
        # For Lambda, pre-package your pipelines or download from a repository
        spec = importlib.util.find_spec(f"pipelines")
        if spec is None:
            raise ImportError(f"Module 'pipelines' not found")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, pipeline_name):
            raise AttributeError(f"Pipeline '{pipeline_name}' not found in module")
        
        return getattr(module, pipeline_name)
    except Exception as e:
        logger.error(f"Failed to import pipeline: {str(e)}")
        raise

def lambda_handler(event, context):
    """AWS Lambda handler to trigger a ZenML pipeline."""
    try:
        # Parse the request
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        pipeline_name = body.get('pipeline_name')
        parameters = body.get('parameters', {})
        
        if not pipeline_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing pipeline_name in request'})
            }
        
        # Validate API key if needed
        headers = event.get('headers', {})
        api_key = headers.get('X-API-Key')
        expected_key = os.environ.get('PIPELINE_API_KEY')
        
        if expected_key and api_key != expected_key:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid API key'})
            }
        
        # Import and run the pipeline
        pipeline_func = import_pipeline(pipeline_name)
        run = pipeline_func(**parameters)
        
        logger.info(f"Pipeline '{pipeline_name}' triggered successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'message': f"Pipeline '{pipeline_name}' triggered successfully",
                'run_id': run.id if hasattr(run, 'id') else None
            })
        }
    except Exception as e:
        logger.error(f"Error triggering pipeline: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to trigger pipeline: {str(e)}'})
        }
```

### Deploying the Lambda Function

1. Package your code and dependencies:

```bash
# Create a directory for your Lambda function
mkdir -p lambda_package/python

# Install dependencies to the package directory
pip install zenml -t lambda_package/python

# Copy your pipeline module
cp -r pipelines lambda_package/python/

# Copy the Lambda handler
cp lambda_function.py lambda_package/

# Create a deployment package
cd lambda_package
zip -r ../lambda_deployment_package.zip .
cd ..
```

2. Deploy the Lambda function (using AWS CLI):

```bash
aws lambda create-function \
  --function-name zenml-pipeline-trigger \
  --runtime python3.9 \
  --role arn:aws:iam::123456789012:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment_package.zip \
  --timeout 300 \
  --environment Variables="{PIPELINE_API_KEY=your-secure-api-key}"
```

3. Create an API Gateway to expose the Lambda function:

```bash
# Create an API
aws apigateway create-rest-api --name ZenML-Pipeline-API

# Get the API ID and create resources and methods
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='ZenML-Pipeline-API'].id" --output text)
PARENT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/'].id" --output text)

# Create a /trigger resource
aws apigateway create-resource --rest-api-id $API_ID --parent-id $PARENT_RESOURCE_ID --path-part "trigger"
RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/trigger'].id" --output text)

# Create a POST method
aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID \
  --http-method POST --authorization-type NONE \
  --api-key-required true

# Integrate with the Lambda function
aws apigateway put-integration --rest-api-id $API_ID --resource-id $RESOURCE_ID \
  --http-method POST --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:zenml-pipeline-trigger/invocations
```

### Triggering via the Lambda Function

Now you can trigger your pipeline by calling the API Gateway endpoint:

```bash
curl -X POST \
  https://$API_ID.execute-api.$REGION.amazonaws.com/prod/trigger \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-secure-api-key' \
  -d '{
    "pipeline_name": "training_pipeline",
    "parameters": {
      "data_url": "s3://some-bucket/new-data.csv",
      "model_type": "gradient_boosting"
    }
  }'
```

## Method 4: Integrating with GitHub Actions

GitHub Actions provides a way to trigger pipelines based on events or schedules, which is perfect for CI/CD integration.

### Setting Up a GitHub Action for Scheduled Runs

Create a file `.github/workflows/scheduled-training.yml`:

```yaml
name: Scheduled Model Training

on:
  # Run on schedule (UTC time)
  schedule:
    - cron: '0 4 * * *'  # Run daily at 4 AM UTC
  
  # Allow manual trigger
  workflow_dispatch:
    inputs:
      data_url:
        description: 'URL of the dataset to use'
        required: true
        default: 's3://default-bucket/data.csv'
      model_type:
        description: 'Type of model to train'
        required: true
        default: 'random_forest'
        type: choice
        options:
          - random_forest
          - gradient_boosting

jobs:
  trigger-training:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install zenml
          # Install any other required packages
          
      - name: Configure ZenML
        run: |
          # Set up ZenML connection to your server
          zenml connect --url ${{ secrets.ZENML_SERVER_URL }} \
                       --username ${{ secrets.ZENML_USERNAME }} \
                       --password ${{ secrets.ZENML_PASSWORD }}
          
          # Set the active stack (if needed)
          zenml stack set ${{ secrets.ZENML_STACK_NAME }}
      
      - name: Trigger pipeline
        run: |
          # For scheduled runs, use default values
          if [ "${{ github.event_name }}" == "schedule" ]; then
            python -c "
from pipelines import training_pipeline
training_pipeline(
    data_url='s3://scheduled-bucket/daily-data.csv',
    model_type='random_forest'
)
"
          # For manual runs, use the provided inputs
          else
            python -c "
from pipelines import training_pipeline
training_pipeline(
    data_url='${{ github.event.inputs.data_url }}',
    model_type='${{ github.event.inputs.model_type }}'
)
"
          fi
```

### Setting Up GitHub Secrets

To securely store your ZenML credentials, set up GitHub Secrets in your repository:

1. Go to your GitHub repository
2. Click on Settings � Secrets and variables � Actions
3. Add the following secrets:
   - `ZENML_SERVER_URL`: URL of your ZenML server
   - `ZENML_USERNAME`: Your ZenML username
   - `ZENML_PASSWORD`: Your ZenML password
   - `ZENML_STACK_NAME`: Name of your ZenML stack

### Implementing Event-Driven Triggers

You can also trigger the pipeline based on GitHub events, such as when new data is pushed to a specific branch:

```yaml
name: Event-Triggered Training

on:
  push:
    branches: [ main ]
    paths:
      - 'data/**'  # Only run when files in the data directory change

jobs:
  trigger-training:
    runs-on: ubuntu-latest
    
    steps:
      # Similar setup steps as above
      
      - name: Determine changed files
        id: changes
        run: |
          # Get the list of changed files
          CHANGED_FILES=$(git diff --name-only ${{ github.event.before }} ${{ github.event.after }} | grep '^data/' || true)
          echo "Changed files: $CHANGED_FILES"
          
          # Extract the data path from the first changed file
          if [ -n "$CHANGED_FILES" ]; then
            FIRST_FILE=$(echo "$CHANGED_FILES" | head -n 1)
            echo "first_file=$FIRST_FILE" >> $GITHUB_OUTPUT
          fi
      
      - name: Trigger pipeline with changed data
        if: steps.changes.outputs.first_file != ''
        run: |
          python -c "
from pipelines import training_pipeline
training_pipeline(
    data_url='${{ steps.changes.outputs.first_file }}',
    model_type='random_forest'
)
"
```

## Method 5: Pipeline-to-Pipeline Triggering

Sometimes you need one ZenML pipeline to trigger another, such as when a data processing pipeline should trigger a training pipeline upon completion.

### Basic Pipeline-to-Pipeline Triggers

```python
from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact

# Data processing pipeline that will trigger the training pipeline
@step
def process_data() -> str:
    """Process data and return a data URL."""
    # Process data logic...
    return "s3://processed-data-bucket/processed.csv"

@step
def trigger_training_pipeline(data_url: str) -> None:
    """Trigger the training pipeline with the processed data."""
    # Create run configuration with parameters
    run_config = PipelineRunConfiguration(
        pipeline_parameters={
            "data_url": data_url,
            "model_type": "random_forest"
        }
    )
    
    # Trigger the training pipeline
    Client().trigger_pipeline(
        pipeline_name_or_id="training_pipeline",
        run_configuration=run_config
    )
    
    print(f"Triggered training pipeline with data: {data_url}")

@pipeline
def data_processing_pipeline():
    """Pipeline that processes data and triggers training."""
    data_url = process_data()
    trigger_training_pipeline(data_url)
```

### Advanced: Passing Artifacts Between Pipelines

For more complex scenarios, you can pass artifact IDs between pipelines:

```python
from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
import pandas as pd

# First pipeline that creates a dataset
@step
def create_dataset() -> pd.DataFrame:
    """Create a dataset."""
    # Create dataset logic...
    return pd.DataFrame({
        'feature': [1, 2, 3],
        'target': [0, 1, 0]
    })

@step
def trigger_training_with_artifact(dataset: UnmaterializedArtifact) -> None:
    """Trigger training pipeline with a dataset artifact ID."""
    # By using UnmaterializedArtifact, we can access the artifact ID
    run_config = PipelineRunConfiguration(
        steps={
            "load_data_from_artifact": {
                "parameters": {
                    "dataset_artifact_id": dataset.id
                }
            }
        }
    )
    
    Client().trigger_pipeline(
        pipeline_name_or_id="training_with_artifact_pipeline",
        run_configuration=run_config
    )
    
    print(f"Triggered training pipeline with dataset artifact ID: {dataset.id}")

@pipeline
def data_creation_pipeline():
    """Pipeline that creates a dataset and triggers training."""
    dataset = create_dataset()
    trigger_training_with_artifact(dataset)

# The second pipeline that consumes the artifact
@step
def load_data_from_artifact(dataset_artifact_id: str) -> pd.DataFrame:
    """Load dataset from artifact store using its ID."""
    from zenml.artifacts.utils import load_artifact
    
    # Load the artifact by ID
    dataset = load_artifact(dataset_artifact_id)
    print(f"Loaded dataset with ID: {dataset_artifact_id}")
    return dataset

@step
def train_with_artifact(dataset: pd.DataFrame) -> None:
    """Train a model using the provided dataset."""
    # Training logic...
    print(f"Training with dataset of shape: {dataset.shape}")

@pipeline
def training_with_artifact_pipeline():
    """Pipeline that trains using a dataset artifact."""
    dataset = load_data_from_artifact()
    train_with_artifact(dataset)
```

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

### Common Issues and Solutions

#### Issue: Authentication Failures

```python
# Test your authentication before attempting to trigger
try:
    Client().zen_store.verify_connection()
    print("Authentication successful")
except Exception as e:
    print(f"Authentication failed: {str(e)}")
    # Implement retry logic or alerting
```

#### Issue: Missing Dependencies in Serverless Environments

Package a complete virtual environment with your serverless function:

```bash
# Create a requirements.txt file with pinned versions
pip freeze > requirements.txt

# For AWS Lambda, package dependencies correctly
pip install --target ./lambda_package/python -r requirements.txt
```

#### Issue: Timeouts on Long-Running Operations

For APIs that trigger pipelines, implement asynchronous responses:

```python
@app.post("/trigger-async")
async def trigger_pipeline_async(request: PipelineRequest):
    """Trigger a pipeline asynchronously."""
    # Start a background task and return immediately
    import threading
    
    def run_pipeline():
        try:
            pipeline_func = import_pipeline(request.pipeline_name)
            pipeline_func(**request.parameters)
            logger.info(f"Async pipeline '{request.pipeline_name}' completed")
        except Exception as e:
            logger.error(f"Async pipeline '{request.pipeline_name}' failed: {str(e)}")
    
    # Start the pipeline in a background thread
    thread = threading.Thread(target=run_pipeline)
    thread.start()
    
    return {"status": "accepted", "message": "Pipeline triggered asynchronously"}
```

## Conclusion: Choosing the Right Approach

The best approach for triggering pipelines depends on your specific needs:

1. **ZenML Pro Run Templates**: Ideal for teams that need a complete, managed solution with UI support and centralized management

2. **Custom API**: Best for teams that need full control over the triggering mechanism and want to embed it within their own infrastructure

3. **Serverless Functions**: Perfect for event-driven workflows with minimal infrastructure management

4. **GitHub Actions**: Excellent for teams already using GitHub and needing CI/CD integration

5. **Pipeline-to-Pipeline Triggers**: Useful for complex ML workflows where pipelines depend on each other

Regardless of your approach, always prioritize:
- Security (authentication and authorization)
- Reliability (error handling and retries)
- Observability (logging and monitoring)

## Next Steps

Now that you understand how to trigger ZenML pipelines from external systems, consider exploring:

1. [Managing scheduled pipelines](managing-scheduled-pipelines.md) for time-based execution
2. Implementing [comprehensive CI/CD](https://docs.zenml.io/user-guides/production-guide/ci-cd) for your ML workflows
3. Setting up [monitoring and alerting](https://docs.zenml.io/stacks/alerters)
   for pipeline failures
