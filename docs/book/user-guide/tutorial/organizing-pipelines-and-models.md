---
description: >-
  A step-by-step tutorial on effectively organizing your ML assets in ZenML
  using tags and projects
icon: inbox-full
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Organizing pipelines and models

This cookbook demonstrates how to effectively organize your machine learning assets in ZenML using tags and projects. We'll implement a fraud detection system while applying increasingly sophisticated organization techniques.

## Introduction: The Organization Challenge

As ML projects grow, effective organization becomes critical. ZenML provides two powerful organization mechanisms:

1. **Tags**: Flexible labels that can be applied to various entities (pipelines, runs, artifacts, models)
2. **Projects** (ZenML Pro): Namespace-based isolation for logical separation\
   between initiatives or teams

{% hint style="info" %}
For our full reference documentation on things covered in this tutorial, see the [Tagging](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/tagging) page, the [Projects](https://docs.zenml.io/pro/core-concepts/projects) page, and the [Model Control Plane](https://docs.zenml.io/how-to/model-management-metrics/model-control-plane) page.
{% endhint %}

## Prerequisites

Before starting this tutorial, make sure you have:

1. ZenML installed and configured
2. Basic understanding of ZenML pipelines and steps
3. [ZenML Pro](https://zenml.io/pro) account (for the Projects section only)

## Part 1: Basic Pipeline Organization with Tags

### Creating and Tagging a Simple Pipeline

Let's create a basic fraud detection pipeline with tags:

```python
from typing import Tuple

from zenml import pipeline, step
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# Define steps for our pipeline
@step
def load_data() -> pd.DataFrame:
    """Load transaction data."""
    # Simulate transaction data
    np.random.seed(42)
    n_samples = 1000
    data = pd.DataFrame({
        'amount': np.random.normal(100, 50, n_samples),
        'transaction_count': np.random.poisson(5, n_samples),
        'merchant_category': np.random.randint(1, 20, n_samples),
        'time_of_day': np.random.randint(0, 24, n_samples),
        'is_fraud': np.random.choice([0, 1], n_samples, p=[0.95, 0.05])
    })
    return data

@step
def prepare_data(
    data: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Prepare data for training."""
    X = data.drop("is_fraud", axis=1)
    y = data["is_fraud"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train, X_test, y_train, y_test

@step
def train_model(X_train, y_train) -> RandomForestClassifier:
    """Train a fraud detection model."""
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    return model

@step
def evaluate_model(model: RandomForestClassifier, X_test, y_test) -> float:
    """Evaluate the model."""
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model accuracy: {accuracy:.4f}")
    return accuracy

# Apply tags to the pipeline
@pipeline(tags=["fraud-detection", "training", "development"])
def fraud_detection_pipeline():
    """A simple pipeline for fraud detection."""
    data = load_data()
    X_train, X_test, y_train, y_test = prepare_data(data)
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)

# Run the pipeline
fraud_detection_pipeline()
```

### Adding Tags at Runtime

You can add tags when running a pipeline:

```python
# Using with_options
configured_pipeline = fraud_detection_pipeline.with_options(
    tags=["random-forest", "daily-run"]
)
configured_pipeline()

# Or with a YAML configuration file
# config.yaml contains:
# tags:
#   - config-tag
#   - experiment-001

configured_pipeline = fraud_detection_pipeline.with_options(config_path="config.yaml")
configured_pipeline()
```

### Finding Pipelines by Tags

```python
from zenml.client import Client
from rich import print

client = Client()
fraud_pipelines = client.list_pipeline_runs(tags=["fraud-detection"])

print(f"Found {len(fraud_pipelines.items)} fraud detection pipeline runs:")
for pipeline in fraud_pipelines.items:
    tag_names = [tag.name for tag in pipeline.tags]
    print(f"  - {pipeline.name} (tags: {', '.join(tag_names)})")

```

## Part 2: Organizing Artifacts with Tags

### Tagging Artifacts During Creation

Use `ArtifactConfig` to tag artifacts as they're created:

```python
from zenml import step, ArtifactConfig
from typing import Annotated

@step
def load_data() -> Annotated[
    pd.DataFrame,
    ArtifactConfig(
        name="transaction_data", tags=["raw", "financial", "daily"]
    ),
]:
    """Load transaction data with tags applied to the artifact."""
    # Implementation same as before
    # ...
    return data

@step
def feature_engineering(data: pd.DataFrame) -> Annotated[
    pd.DataFrame,
    ArtifactConfig(
        name="feature_data", tags=["processed", "financial"]
    ),
]:
    """Create features for fraud detection."""
    # Add some features
    data['amount_squared'] = data['amount'] ** 2
    data['late_night'] = (data['time_of_day'] >= 23) | (data['time_of_day'] <= 4)
    return data
```

### Tagging Artifacts Dynamically

```python
from zenml import add_tags

@step
def evaluate_data_quality(data: pd.DataFrame) -> Annotated[
    float,
    ArtifactConfig(
        name="data_quality", tags=["evaluation"]
    ),
]:
    """Evaluate data quality and tag the input artifact accordingly."""
    # Check for missing values
    missing_percentage = data.isnull().mean().mean() * 100
    
    # Tag based on quality assessment
    if missing_percentage == 0:
        add_tags(tags=["complete-data"], artifact_name="data_quality", infer_artifact=True)
    else:
        add_tags(tags=["incomplete-data"], artifact_name="data_quality", infer_artifact=True)
    
    return missing_percentage
```

### Finding Tagged Artifacts

```python
from zenml.client import Client

client = Client()
raw_financial_data = client.list_artifact_versions(tags=["raw", "financial"])

print(f"Found {len(raw_financial_data.items)} raw financial data artifacts")
```

## Part 3: Model Organization with Tags

### Creating and Tagging Models

```python
from zenml import Model
from zenml import pipeline

# Create a model with tags
fraud_model = Model(
    name="fraud_detector",
    version="1.0.0",
    tags=["random-forest", "baseline", "financial"]
)

# Associate model with a pipeline
@pipeline(model=fraud_model)
def model_training_pipeline():
    data = load_data()
    processed_data = feature_engineering(data)
    X_train, X_test, y_train, y_test = prepare_data(processed_data)
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)
    tag_model_with_metrics(accuracy)  # Tag with performance metrics
```

## Part 4: Advanced Tagging Techniques

### Exclusive Tags for Production Tracking

```python
from zenml import pipeline, Tag

# Only one pipeline can have this tag at a time
@pipeline(tags=[Tag(name="production", exclusive=True)])
def production_fraud_pipeline():
    # Pipeline implementation
    # ...
```

Read more about exclusive tags [here](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/tagging#exclusive-tags).

### Cascade Tags for Automatic Artifact Tagging

```python
# Tag propagates to all artifacts created during pipeline execution
@pipeline(tags=[Tag(name="financial-domain", cascade=True)])
def domain_tagged_pipeline():
    # Pipeline implementation
    # ...
```

Read more about cascade tags [here](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/tagging#cascade-tags).

### Advanced Tag Filtering

```python
# Find models with accuracy above 90%
high_accuracy_models = client.list_models(
    tags=["startswith:accuracy-9", "random-forest"]
)

# Find all processed financial artifact versions
financial_processed = client.list_artifact_versions(
    tags=["financial", "contains:process"]
)
```

## Part 5: Organizing with Projects (ZenML Pro)

Projects provide logical separation between different initiatives or teams.

### Creating and Setting a Project

```python
from zenml.client import Client

# Create a project
Client().create_project(
    name="fraud-detection",
    description="ML models for detecting fraudulent transactions"
)

# Set as active project
Client().set_active_project("fraud-detection")
```

You can also use the CLI:

```bash
# Create and activate a project
zenml project register fraud-detection --display-name "Fraud Detection" --set
```

### Implementing Cross-Project Organization

For consistency across projects, use a standardized tagging strategy:

```python
# Define consistent tag categories across projects
ENVIRONMENTS = ["environment-development", "environment-staging", "environment-production"]
DOMAINS = ["domain-credit-card", "domain-wire-transfer", "domain-account"]
STATUSES = ["status-experimental", "status-validated", "status-production"]

# Use in your pipelines
@pipeline(tags=["environment-development", "domain-credit-card"])
def credit_card_fraud_pipeline():
    # Pipeline implementation
    # ...
```

## Part 6: Practical Organization Patterns

### Create a Tag Registry for Consistency

```python
# tag_registry.py
from enum import Enum

class Environment(Enum):
    """Environment tags."""
    DEV = "environment-development"
    STAGING = "environment-staging"
    PRODUCTION = "environment-production"

class Domain(Enum):
    """Domain tags."""
    CREDIT_CARD = "domain-credit-card"
    WIRE_TRANSFER = "domain-wire-transfer"

class Status(Enum):
    """Status tags."""
    EXPERIMENTAL = "status-experimental"
    VALIDATED = "status-validated"
    PRODUCTION = "status-production"

# Usage
from tag_registry import Environment, Domain, Status

@pipeline(tags=[Environment.DEV.value, Domain.CREDIT_CARD.value])
def pipeline_with_consistent_tags():
    # Implementation
    pass
```

### Find and Fix Orphaned Resources

```python
from zenml.client import Client

def find_untagged_resources():
    """Find resources without organization tags."""
    client = Client()
    
    # Check for models without environment tags
    all_models = client.list_models().items
    untagged_models = []
    
    env_tags = ["environment-development", "environment-staging", "environment-production"]
    
    for model in all_models:
        if not any(tag in model.tags for tag in env_tags):
            untagged_models.append(model)
    
    print(f"Found {len(untagged_models)} models without environment tags")
    return untagged_models
```

## Conclusion and Best Practices

A well-designed tagging strategy helps maintain organization as your ML project grows:

1. **Use consistent tag naming conventions** - Create a tag registry to ensure consistency
2. **Apply tags at all levels** - Tag pipelines, runs, artifacts, and models
3. **Create meaningful tag categories** - Environment, domain, status, algorithm type, etc.
4. **Use exclusive tags for state management** - Perfect for tracking current production models
5. **Combine tags with projects** for complete organization - Use projects for major boundaries, tags for cross-cutting concerns
6. **Document your tagging strategy** - Ensure everyone on the team follows the same conventions

## Next Steps

Now that you understand how to organize your ML assets, consider exploring:

1. [Managing scheduled pipelines](../tutorial/managing-scheduled-pipelines.md) to automate your ML workflows
2. Integrating your tagging strategy with [CI/CD pipelines](https://docs.zenml.io/user-guides/production-guide/ci-cd)
3. [Ways to trigger pipelines](https://docs.zenml.io/how-to/trigger-pipelines)
