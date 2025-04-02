---
description: A step-by-step tutorial on setting up CI/CD for your ML pipelines with ZenML and GitHub Actions
---

# Continuous Integration and Deployment for ML Pipelines

This tutorial demonstrates how to implement Continuous Integration and Continuous Deployment (CI/CD) workflows for your ML pipelines using ZenML. You'll learn how to automate testing, validation, and deployment of your ML pipelines through a practical example using GitHub Actions.

## Understanding CI/CD for ML Pipelines

In traditional software development, CI/CD helps ensure code quality and automate deployments. For ML, these practices extend beyond just code testing - we need to validate data quality, model performance, and ensure reproducibility across environments.

With ZenML, you can:
- Automatically test pipeline code and model quality 
- Deploy validated models to production
- Ensure consistent environments from development to production
- Track and version both code and models

## Prerequisites

Before starting this tutorial, you should have:

1. ZenML installed and configured with a remote server
2. A GitHub repository containing a ZenML pipeline
3. Basic familiarity with GitHub Actions

## Creating a Simple ML Pipeline for CI/CD

Let's start with a basic ML pipeline that we'll use throughout this tutorial. Create a file named `pipelines.py`:

```python
from zenml import pipeline, step
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

@step
def load_data() -> pd.DataFrame:
    """Load a simple dataset."""
    # In a real scenario, you might load from different sources
    # based on environment (dev/staging/prod)
    from sklearn.datasets import load_iris
    data = load_iris(as_frame=True)
    return data.frame

@step
def preprocess_data(data: pd.DataFrame) -> tuple:
    """Preprocess the data and split into train/test."""
    X = data.drop("target", axis=1)
    y = data["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train, X_test, y_train, y_test

@step
def train_model(train_data: tuple) -> object:
    """Train a simple model."""
    X_train, _, y_train, _ = train_data
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    return model

@step
def evaluate_model(model: object, test_data: tuple) -> float:
    """Evaluate model performance."""
    _, X_test, _, y_test = test_data
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model accuracy: {accuracy:.4f}")
    return accuracy

@pipeline
def training_pipeline():
    """A simple pipeline for training and evaluation."""
    data = load_data()
    train_test_data = preprocess_data(data)
    model = train_model(train_test_data)
    accuracy = evaluate_model(model, train_test_data)
```

This pipeline is intentionally simple but demonstrates the core components of an ML workflow: data loading, preprocessing, training, and evaluation. We'll extend this pipeline for CI/CD in the following steps.

## Setting Up ML-Specific CI/CD Environments

### Creating Development and Production Stacks

ML pipelines need to run in different environments as they move from development to production. With ZenML, you can create separate stacks to isolate these environments.

```bash
# Create development stack (for local testing)
zenml stack register dev-stack \
  -o local \
  -a local_artifact_store

# Create production stack (for deployment)
# Replace components with your actual stack components
zenml stack register prod-stack \
  -o kubernetes \
  -a s3 \
  -e mlflow
```

{% hint style="info" %}
For a production environment, you'll need to configure the MLflow experiment tracker with appropriate settings:

```bash
# Register an MLflow experiment tracker component
zenml experiment-tracker register mlflow_tracker \
    --flavor=mlflow \
    --tracking_uri=https://your-mlflow-server-url \
    --tracking_username=your_username \  # Optional
    --tracking_password=your_password    # Optional
```

If you're using a locally-hosted MLflow server, you can use `--tracking_uri=http://localhost:5000`
{% endhint %}

If you already have stacks configured, you can use them for this tutorial.

### Setting Up Authentication for CI/CD

For CI/CD systems to interact with ZenML, we need to create a service account and API key:

```bash
# Create a service account for GitHub Actions
zenml service-account create github_actions

# Generate an API key (save this securely)
zenml service-account api-key github_actions create github_actions_key
```

{% hint style="info" %}
The API key will be shown only once. Make sure to copy it immediately and store it securely.
{% endhint %}

### Configuring GitHub Secrets

In your GitHub repository, add these secrets:
- `ZENML_SERVER_URL`: URL of your ZenML server (e.g., `https://your-zenml-server.com`)
- `ZENML_API_KEY`: The API key generated above

To add secrets in GitHub:
1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with its appropriate value

![Adding GitHub Secrets](../../.gitbook/assets/github_secrets_example.png)

## Building a CI Workflow with Quality Checks

Let's enhance our pipeline with quality verification for CI testing. Create a file named `ci_pipeline.py`:

```python
from pipelines import (
    load_data, preprocess_data, train_model, evaluate_model
)
from zenml import pipeline, step

@step
def verify_model_quality(accuracy: float, threshold: float = 0.8) -> bool:
    """Verify that model meets quality threshold."""
    if accuracy >= threshold:
        print(f"Model meets quality threshold: {accuracy:.4f} >= {threshold}")
        return True
    else:
        print(f"Model quality below threshold: {accuracy:.4f} < {threshold}")
        return False

@pipeline
def ci_pipeline(quality_threshold: float = 0.8):
    """Pipeline for CI that includes quality verification."""
    data = load_data()
    train_test_data = preprocess_data(data)
    model = train_model(train_test_data)
    accuracy = evaluate_model(model, train_test_data)
    meets_threshold = verify_model_quality(accuracy, quality_threshold)
```

Now, let's create a simple entry point script `run.py` that will be used by our CI/CD workflow:

```python
import argparse
from ci_pipeline import ci_pipeline
from production_pipeline import production_pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", choices=["ci", "production"], required=True)
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    
    if args.pipeline == "ci":
        ci_pipeline(quality_threshold=args.threshold)
    elif args.pipeline == "production":
        production_pipeline()
```

### Automating CI with GitHub Actions

Create a file `.github/workflows/ml-pipeline-ci.yml` in your repository:

```yaml
name: ML Pipeline CI

on:
  pull_request:
    branches: [ main ]

jobs:
  test-pipeline:
    runs-on: ubuntu-latest
    env:
      ZENML_SERVER_URL: ${{ secrets.ZENML_SERVER_URL }}
      ZENML_API_KEY: ${{ secrets.ZENML_API_KEY }}
    
    steps:
      - name: Check out repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install zenml scikit-learn pandas
          # Add any other dependencies your pipeline needs

      - name: Connect to ZenML server
        run: |
          zenml connect --url $ZENML_SERVER_URL --api-key $ZENML_API_KEY

      - name: Set development stack
        run: |
          zenml stack set dev-stack

      - name: Run CI pipeline
        run: |
          python run.py --pipeline ci --threshold 0.8
```

This workflow will:
1. Trigger on pull requests to the main branch
2. Connect to your ZenML server using the stored secrets
3. Set the development stack for testing
4. Run the CI pipeline with a quality threshold of 0.8

## Implementing CD for Model Deployment

Now, let's create a production pipeline that includes model deployment logic. Create a file `production_pipeline.py`:

```python
from pipelines import (
    load_data, preprocess_data, train_model, evaluate_model
)
from ci_pipeline import verify_model_quality
from zenml import pipeline, step
import mlflow
import os

@step(experiment_tracker="mlflow")
def save_model(model: object, accuracy: float) -> str:
    """Save the model to MLflow and return the model URI."""
    # When using ZenML's experiment tracker, MLflow is already configured
    # Register the model in MLflow
    mlflow.sklearn.log_model(model, "model")
    model_uri = mlflow.get_artifact_uri("model")
    
    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    
    print(f"Model saved with URI: {model_uri}")
    print(f"Model accuracy: {accuracy:.4f}")
    
    # In a real scenario, you might also:
    # - Tag the model with metadata
    # - Register it in a model registry
    # - Deploy it to a serving infrastructure
    
    return model_uri

@pipeline
def production_pipeline(quality_threshold: float = 0.85):
    """Pipeline for production deployment."""
    data = load_data()
    train_test_data = preprocess_data(data)
    model = train_model(train_test_data)
    accuracy = evaluate_model(model, train_test_data)
    meets_threshold = verify_model_quality(accuracy, threshold=quality_threshold)
    if meets_threshold:
        model_uri = save_model(model, accuracy)
```

{% hint style="info" %}
The `experiment_tracker="mlflow"` parameter in the `@step` decorator tells ZenML to use the MLflow experiment tracker component from your stack. ZenML automatically configures the MLflow context, so you don't need to set up the tracking URI or experiment name manually.

After running the pipeline, you can access the MLflow UI using:

```python
from zenml.client import Client

# Get the latest run
pipeline_run = Client().get_pipeline_run(pipeline_name="production_pipeline")

# Get the experiment tracker URL
experiment_tracker = Client().active_stack.experiment_tracker
if experiment_tracker and experiment_tracker.flavor == "mlflow":
    print(f"MLflow UI URL: {experiment_tracker.config.tracking_uri}")
```
{% endhint %}

### Automating Deployment with GitHub Actions

Create a file `.github/workflows/ml-pipeline-cd.yml` in your repository:

```yaml
name: ML Pipeline CD

on:
  push:
    branches: [ main ]

jobs:
  deploy-pipeline:
    runs-on: ubuntu-latest
    env:
      ZENML_SERVER_URL: ${{ secrets.ZENML_SERVER_URL }}
      ZENML_API_KEY: ${{ secrets.ZENML_API_KEY }}
      # If your MLflow server requires credentials, add them here
      # MLFLOW_TRACKING_USERNAME: ${{ secrets.MLFLOW_USERNAME }}
      # MLFLOW_TRACKING_PASSWORD: ${{ secrets.MLFLOW_PASSWORD }}
    
    steps:
      - name: Check out repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install zenml scikit-learn pandas mlflow
          # Add any other dependencies your pipeline needs

      - name: Connect to ZenML server
        run: |
          zenml connect --url $ZENML_SERVER_URL --api-key $ZENML_API_KEY

      - name: Set production stack
        run: |
          zenml stack set prod-stack

      - name: Run production pipeline
        run: |
          python run.py --pipeline production
          
      - name: Get MLflow experiment URL
        run: |
          echo "Check the MLflow UI for experiment results"
          python -c "
from zenml.client import Client
experiment_tracker = Client().active_stack.experiment_tracker
if experiment_tracker and experiment_tracker.flavor == 'mlflow':
    print(f'MLflow UI: {experiment_tracker.config.tracking_uri}')
"
```

This workflow will:
1. Trigger when code is pushed to the main branch
2. Connect to your ZenML server using the stored secrets
3. Set the production stack
4. Run the production pipeline
5. Print the MLflow UI URL to check experiment results

{% hint style="info" %}
If your MLflow tracking server requires authentication, you should add the credentials as GitHub secrets and include them in the environment variables.
{% endhint %}

## Standardizing Deployments with Run Templates (Pro Feature)

{% hint style="success" %}
This section covers ZenML Pro features that streamline deployment
{% endhint %}

ZenML Pro offers Run Templates, which provide a powerful way to standardize and trigger pipeline runs, especially useful in CD workflows. After you've run your production pipeline successfully, you can create a template from that run:

```python
from zenml.client import Client
from zenml.config import PipelineRunConfiguration

# Get a previous successful pipeline run
successful_run = Client().get_pipeline_run("<PIPELINE_RUN_ID>")

# Create a template from this run
template = Client().create_run_template(
    name="production-model-template", 
    deployment_id=successful_run.deployment_id
)

print(f"Created template: {template.name} with ID: {template.id}")
```

This template can then be used to trigger standardized runs:

```python
from zenml.client import Client
from zenml.config import PipelineRunConfiguration

# Configure parameters as needed
run_config = PipelineRunConfiguration(
    pipeline_parameters={
        "quality_threshold": 0.85
    }
)

# Trigger run from template (can be used in CD)
Client().trigger_pipeline(
    template_id="<TEMPLATE_ID>",
    run_configuration=run_config
)
```

You can integrate this into your CD workflow to ensure consistent pipeline execution.

## Putting It All Together: The Complete CI/CD Workflow

The complete workflow now looks like this:

1. **Development**: Develop and test pipelines locally
2. **CI**: Create a pull request to trigger the CI workflow:
   - Pipeline runs on the development stack
   - Quality verification ensures model performance meets standards
   - Code review and CI success are required to merge
3. **CD**: Merge to main branch triggers the CD workflow:
   - Pipeline runs on the production stack
   - Model is saved and registered if it meets quality standards
   - (Optionally) Model is deployed to serving infrastructure

## Best Practices for ML CI/CD

### Version Everything

- **Code**: Use Git for version control
- **Models**: ZenML automatically tracks model artifacts
- **Data**: Consider data versioning for full reproducibility

### Ensure Environment Consistency

- Use ZenML stacks to define consistent environments
- Consider containerization for full reproducibility
- Pin dependency versions in your requirements.txt

### Test Both Code and Model Quality

- Include data validation steps
- Set performance thresholds for model metrics
- Consider A/B testing for new models

### Monitor Deployed Models

- Track model performance in production
- Set up alerting for performance degradation
- Have a rollback strategy ready

## Common Issues and Solutions

### Authentication Problems

- Verify API keys are set correctly in GitHub Secrets
- Check that service accounts have appropriate permissions
- Ensure keys haven't expired

### Resource Constraints

- Configure resource limits appropriately for training jobs
- Consider using step operators for resource-intensive steps
- Break large pipelines into manageable pieces

### Pipeline Configuration Issues

- Use ZenML's typing system to catch errors early
- Verify stack components are compatible
- Test configuration changes locally before pushing to CI/CD

## Conclusion

In this tutorial, you've learned how to implement a CI/CD workflow for ML pipelines using ZenML and GitHub Actions. By automating testing and deployment, you can ensure that only high-quality models make it to production, while maintaining reproducibility across environments.

This approach combines the best practices of software engineering with the unique requirements of ML, resulting in more reliable, reproducible, and maintainable ML systems.

## Next Steps

- Learn about [Managing scheduled pipelines](managing-scheduled-pipelines.md)
- Explore [Organizing pipelines and models](organizing-pipelines-and-models.md)
- Check out the [ZenML GitFlow Repository](https://github.com/zenml-io/zenml-gitflow) for a complete example