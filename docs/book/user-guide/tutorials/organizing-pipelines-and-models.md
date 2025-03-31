---
description: A step-by-step tutorial on effectively organizing your ML assets in ZenML using tags and projects
---

# Organizing Pipelines, Models, and Artifacts: A Cookbook

This cookbook demonstrates how to effectively organize your machine learning assets in ZenML through a practical example. We'll implement a fraud detection system while applying increasingly sophisticated organization techniques as our project grows in complexity.

## Introduction: The Organization Challenge

As machine learning projects grow, effective organization becomes critical. More models, more data, more experiments, and more team members all contribute to potential chaos without proper structure. ZenML provides two powerful organization mechanisms:

1. **Tags**: Flexible, cross-cutting labels that can be applied to various entities (pipelines, runs, artifacts, models)
2. **Projects** (ZenML Pro): Namespace-based isolation for logical separation between initiatives or teams

We'll explore both approaches through a practical scenario: building a fraud detection system for financial transactions.

## Prerequisites

Before starting this tutorial, make sure you have:

1. ZenML installed and configured
2. Basic understanding of ZenML pipelines and steps
3. ZenML Pro account (for the Projects section only)

## Part 1: Getting Started with Basic Tagging

Let's start by creating a simple pipeline for our fraud detection system and apply basic tagging.

### Step 1: Create a Simple Pipeline

First, let's create a basic pipeline with a few steps:

```python
from zenml import pipeline, step
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

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
def prepare_data(data: pd.DataFrame) -> tuple:
    """Prepare data for training."""
    X = data.drop('is_fraud', axis=1)
    y = data['is_fraud']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
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

@pipeline
def fraud_detection_pipeline():
    """A simple pipeline for fraud detection."""
    data = load_data()
    X_train, X_test, y_train, y_test = prepare_data(data)
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)
```

### Step 2: Apply Basic Tags to Pipelines

Now, let's apply tags to make our pipeline more discoverable:

```python
from zenml import pipeline, step

# Using tags in the pipeline decorator
@pipeline(tags=["fraud-detection", "training", "development"])
def fraud_detection_pipeline():
    # Pipeline implementation (same as above)
    data = load_data()
    X_train, X_test, y_train, y_test = prepare_data(data)
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)

# Execute the pipeline
fraud_detection_pipeline()
```

### Step 3: Using Tags with Configuration

You can also apply tags using the `with_options` method, which is useful for runtime configuration:

```python
# Configure the pipeline with additional tags
configured_pipeline = fraud_detection_pipeline.with_options(
    tags=["random-forest", "daily-run"]
)

# Run the configured pipeline
configured_pipeline()
```

Or, create a configuration file:

```yaml
# config.yaml
tags:
  - config-tag
  - experiment-001
```

And run the pipeline with the configuration:

```python
from zenml.config import Source

# Load configuration from file
config_source = Source.from_yaml("config.yaml") 
configured_pipeline = fraud_detection_pipeline.with_options(config_source=config_source)
configured_pipeline()
```

### Step 4: Finding Pipelines by Tags

Now that we've tagged our pipelines, we can easily filter and find them:

```python
from zenml.client import Client

# Get the client
client = Client()

# List all pipelines with the 'fraud-detection' tag
fraud_pipelines = client.list_pipelines(tags=["fraud-detection"])

print(f"Found {len(fraud_pipelines.items)} fraud detection pipelines:")
for pipeline in fraud_pipelines.items:
    print(f"  - {pipeline.name} (tags: {', '.join(pipeline.tags)})")
```

## Part 2: Implementing a Tagging Strategy for Artifacts

As our project grows, we need to track and organize our data artifacts. Let's implement a strategy for tagging artifacts.

### Step 1: Tagging Artifacts During Creation

Using `ArtifactConfig`, we can tag artifacts as they're created:

```python
from zenml import step, ArtifactConfig
from typing import Annotated
import pandas as pd

@step
def load_data() -> Annotated[pd.DataFrame, ArtifactConfig(name="transaction_data", tags=["raw", "financial", "daily"])]:
    """Load transaction data with tags applied to the artifact."""
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
def feature_engineering(data: pd.DataFrame) -> Annotated[pd.DataFrame, 
                                                       ArtifactConfig(name="feature_data", 
                                                                     tags=["processed", "financial"])]:
    """Create features for fraud detection."""
    # Add some features
    data['amount_squared'] = data['amount'] ** 2
    data['late_night'] = (data['time_of_day'] >= 23) | (data['time_of_day'] <= 4)
    return data
```

### Step 2: Tagging Artifacts After Creation

Sometimes you need to tag artifacts dynamically based on their content:

```python
from zenml import add_tags

@step
def evaluate_data_quality(data: pd.DataFrame) -> None:
    """Evaluate data quality and tag the input artifact accordingly."""
    # Check for missing values
    missing_percentage = data.isnull().mean().mean() * 100
    
    # Tag the artifact based on quality checks
    if missing_percentage == 0:
        add_tags(tags=["complete-data"], artifact_name="transaction_data", infer_artifact=True)
    else:
        add_tags(tags=["incomplete-data"], artifact_name="transaction_data", infer_artifact=True)
    
    # Check data volume
    if len(data) > 500:
        add_tags(tags=["high-volume"], artifact_name="transaction_data", infer_artifact=True)
```

### Step 3: Finding Artifacts by Tags

Once artifacts are tagged, we can find them easily:

```python
from zenml.client import Client

# Get the client
client = Client()

# Find all raw financial data artifacts
raw_financial_data = client.list_artifact_versions(
    tags=["raw", "financial"]
)

print(f"Found {len(raw_financial_data.items)} raw financial data artifacts:")
for artifact in raw_financial_data.items:
    print(f"  - {artifact.name} (version: {artifact.version})")
```

## Part 3: Advanced Tagging for Models

As we start building and comparing different models, organizing them becomes crucial.

### Step 1: Creating and Tagging Models

We can use the `Model` class to track our models with tags:

```python
from zenml.models import Model
from zenml import pipeline

# Create a model with tags
fraud_model = Model(
    name="fraud_detector",
    version="1.0.0",
    tags=["random-forest", "baseline", "financial"]
)

# Use the model in a pipeline
@pipeline(model=fraud_model)
def model_training_pipeline():
    data = load_data()
    processed_data = feature_engineering(data)
    X_train, X_test, y_train, y_test = prepare_data(processed_data)
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)
    
    # Optional: we can add performance tags based on results
    return accuracy
```

### Step 2: Tagging Models Based on Performance

We often want to tag models with their performance metrics:

```python
from zenml import add_tags, step

@step
def tag_model_with_metrics(accuracy: float):
    """Tag the model with performance metrics."""
    # Round to 2 decimal places and convert to percentage string
    accuracy_pct = round(accuracy * 100, 2)
    accuracy_tag = f"accuracy-{accuracy_pct}"
    
    # Add tags based on performance thresholds
    add_tags(tags=[accuracy_tag], model_name="fraud_detector", model_version="1.0.0")
    
    if accuracy >= 0.95:
        add_tags(tags=["high-performance"], model_name="fraud_detector", model_version="1.0.0")
    elif accuracy >= 0.90:
        add_tags(tags=["medium-performance"], model_name="fraud_detector", model_version="1.0.0")
    else:
        add_tags(tags=["low-performance"], model_name="fraud_detector", model_version="1.0.0")
```

Update our pipeline to use this step:

```python
@pipeline(model=fraud_model)
def model_training_pipeline():
    data = load_data()
    processed_data = feature_engineering(data)
    X_train, X_test, y_train, y_test = prepare_data(processed_data)
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)
    tag_model_with_metrics(accuracy)
```

### Step 3: Finding Models by Performance Tags

Now we can filter models by their performance:

```python
from zenml.client import Client

# Get the client
client = Client()

# Find high-performance models
high_performance_models = client.list_model_versions(
    tags=["high-performance"]
)

print(f"Found {len(high_performance_models.items)} high-performance models:")
for model in high_performance_models.items:
    print(f"  - {model.name} version {model.version}")
```

## Part 4: Advanced Tag Types and Patterns

As our project matures, we need more sophisticated tagging patterns.

### Step 1: Using Exclusive Tags for Environment Tracking

Exclusive tags ensure only one entity has a particular tag at a time, which is perfect for tracking which model is in production:

```python
from zenml import pipeline, Tag

# Create a pipeline with an exclusive tag for production status
@pipeline(tags=[Tag("production", exclusive=True)])
def production_fraud_pipeline():
    data = load_data()
    processed_data = feature_engineering(data)
    X_train, X_test, y_train, y_test = prepare_data(processed_data)
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)
```

When this pipeline runs, it will become the only pipeline with the "production" tag. Any previously tagged pipeline will lose this tag.

### Step 2: Using Cascade Tags

Cascade tags propagate from a pipeline to all artifacts created during its execution:

```python
from zenml import pipeline, Tag

# Create a pipeline with a cascade tag for domain
@pipeline(tags=[Tag("financial-domain", cascade=True)])
def domain_tagged_pipeline():
    data = load_data()
    processed_data = feature_engineering(data)
    X_train, X_test, y_train, y_test = prepare_data(processed_data)
    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)
```

All artifacts created by this pipeline run will automatically get the "financial-domain" tag.

### Step 3: Advanced Tag Filtering

ZenML supports advanced tag filtering operations:

```python
from zenml.client import Client

# Get the client
client = Client()

# Find models with accuracy greater than 90%
high_accuracy_models = client.list_model_versions(
    tags=["startswith:accuracy-9", "random-forest"]
)

# Find all financial artifacts that are processed
financial_processed = client.list_artifact_versions(
    tags=["financial", "contains:process"]
)
```

### Step 4: Tag Maintenance

As projects evolve, you'll need to update or remove tags:

```python
from zenml.utils.tag_utils import remove_tags

# Remove a deprecated tag
remove_tags(tags=["beta"], model_name="fraud_detector", model_version="1.0.0")

# Replace environment tags on a pipeline
remove_tags(tags=["development"], pipeline="fraud_detection_pipeline")
add_tags(tags=["staging"], pipeline="fraud_detection_pipeline")
```

## Part 5: Scaling Up with Projects (ZenML Pro)

As our team grows, we may need to separate our work into different projects.

{% hint style="success" %}
Projects are a ZenML Pro feature that provides logical separation between different initiatives, teams, or domains.
{% endhint %}

### Step 1: Creating a Project

First, let's create a project for our fraud detection work:

```python
from zenml.client import Client

# Create a new project
Client().create_project(
    name="fraud-detection",
    description="ML models for detecting fraudulent transactions"
)
```

You can also use the CLI:

```bash
zenml project register fraud-detection --display-name "Fraud Detection" --set
```

### Step 2: Setting an Active Project

Before working with resources, set the active project:

```python
from zenml.client import Client

# Set active project
Client().set_active_project("fraud-detection")
```

Or with the CLI:

```bash
zenml project set fraud-detection
```

### Step 3: Working within Project Boundaries

Once a project is active, all operations are scoped to that project:

```python
# Create resources within the active project
@pipeline(tags=["fraud-detection", "research"])
def fraud_research_pipeline():
    # Pipeline implementation
    pass

# List resources in the current project
pipelines = Client().list_pipelines()
```

## Part 6: Combining Projects and Tags

For the most comprehensive organization, combine projects and tags.

### Step 1: Project-specific Tagging Strategy

Define a tagging strategy for each project:

```python
# Fraud Detection Project Tagging Strategy
FRAUD_DOMAINS = ["credit-card", "wire-transfer", "account-takeover"]
FRAUD_ENVIRONMENTS = ["development", "staging", "production"]
FRAUD_MODEL_TYPES = ["random-forest", "xgboost", "neural-network"]
```

### Step 2: Implementing Cross-project Organization

When working across projects, use consistent tag naming:

```python
from zenml.client import Client

# Create projects for different domains
client = Client()

# Create the fraud detection project
client.create_project(
    name="fraud-detection",
    description="ML models for detecting fraudulent transactions"
)

# Create a project for credit scoring
client.create_project(
    name="credit-scoring",
    description="ML models for credit risk assessment"
)

# Use consistent environment tags across projects
for project in ["fraud-detection", "credit-scoring"]:
    client.set_active_project(project)
    
    # Run a pipeline with consistent environment tagging
    @pipeline(tags=["environment-development"])
    def development_pipeline():
        # Pipeline implementation
        pass
    
    development_pipeline()
```

### Step 3: Cross-project Discovery

Find resources across projects with consistent tags:

```python
from zenml.client import Client

# Find all production models across projects
client = Client()
all_projects = client.list_projects()

production_models = []
for project in all_projects.items:
    # Switch to each project
    client.set_active_project(project.name)
    
    # Find production models in this project
    project_production_models = client.list_model_versions(
        tags=["environment-production"]
    )
    
    production_models.extend(project_production_models.items)

print(f"Found {len(production_models)} production models across all projects")
```

## Part 7: Practical Organization Patterns

Let's explore some real-world organization patterns for our fraud detection system.

### Pattern 1: Environment-based Organization

Track models and artifacts across development lifecycle:

```python
from zenml import pipeline, Tag

# Development environment
@pipeline(tags=[Tag("environment-development", exclusive=True)])
def dev_fraud_pipeline():
    # Development implementation
    pass

# Staging environment
@pipeline(tags=[Tag("environment-staging", exclusive=True)])
def staging_fraud_pipeline():
    # Staging implementation with more validation
    pass

# Production environment
@pipeline(tags=[Tag("environment-production", exclusive=True)])
def prod_fraud_pipeline():
    # Production implementation
    pass
```

### Pattern 2: Model Lifecycle Organization

Track models from experimentation to deployment:

```python
from zenml.models import Model

# Experimental model
experiment_model = Model(
    name="fraud_detector",
    version="experiment-001",
    tags=["status-experimental", "algorithm-rf"]
)

# Validated model
validated_model = Model(
    name="fraud_detector",
    version="0.1.0", 
    tags=["status-validated", "algorithm-rf"]
)

# Production model
production_model = Model(
    name="fraud_detector",
    version="1.0.0",
    tags=["status-production", "algorithm-rf"]
)
```

### Pattern 3: Domain-based Organization

Organize models by business domain:

```python
# Credit card fraud models
@pipeline(tags=["domain-credit-card", "fraud-detection"])
def credit_card_fraud_pipeline():
    # Credit card specific implementation
    pass

# Wire transfer fraud models
@pipeline(tags=["domain-wire-transfer", "fraud-detection"])
def wire_transfer_fraud_pipeline():
    # Wire transfer specific implementation
    pass
```

## Part 8: Troubleshooting Common Issues

Here are some practical solutions for common organization issues.

### Issue: Tag Inconsistency

Problem: Inconsistent tag naming causing organizational confusion.

Solution: Create a tag registry utility:

```python
# tag_registry.py
class TagRegistry:
    """Centralized tag registry for consistent naming."""
    
    # Environments
    ENV_DEV = "environment-development"
    ENV_STAGING = "environment-staging" 
    ENV_PRODUCTION = "environment-production"
    
    # Domains
    DOMAIN_CREDIT_CARD = "domain-credit-card"
    DOMAIN_WIRE_TRANSFER = "domain-wire-transfer"
    
    # Status
    STATUS_EXPERIMENTAL = "status-experimental"
    STATUS_VALIDATED = "status-validated"
    STATUS_PRODUCTION = "status-production"

# Usage
from tag_registry import TagRegistry

@pipeline(tags=[TagRegistry.ENV_DEV, TagRegistry.DOMAIN_CREDIT_CARD])
def pipeline_with_consistent_tags():
    # Implementation
    pass
```

### Issue: Finding Orphaned Resources

Problem: Resources without proper organization tags cluttering your workspace.

Solution: Find and tag orphaned resources:

```python
from zenml.client import Client

def find_untagged_resources():
    """Find resources without proper organization tags."""
    client = Client()
    
    # Check for models without environment tags
    all_models = client.list_model_versions().items
    untagged_models = []
    
    env_tags = ["environment-development", "environment-staging", "environment-production"]
    
    for model in all_models:
        if not any(tag in model.tags for tag in env_tags):
            untagged_models.append(model)
    
    print(f"Found {len(untagged_models)} models without environment tags")
    return untagged_models

# Execute the function
orphaned_models = find_untagged_resources()
```

### Issue: Exclusive Tag Behavior

Problem: Unexpected behavior with exclusive tags.

Solution: Check and fix exclusive tag assignments:

```python
from zenml.client import Client

def verify_exclusive_tags(tag_name: str, entity_type: str):
    """Verify that exclusive tags are properly applied."""
    client = Client()
    
    # For example, check pipelines with the 'production' tag
    if entity_type == "pipeline":
        tagged_entities = client.list_pipelines(tags=[tag_name]).items
    elif entity_type == "model":
        tagged_entities = client.list_model_versions(tags=[tag_name]).items
    
    if len(tagged_entities) > 1:
        print(f"WARNING: Found {len(tagged_entities)} {entity_type}s with exclusive tag '{tag_name}'")
        print("This indicates the tag might not be set as exclusive.")
        
        # Fix by recreating the tag as exclusive
        try:
            client.create_tag(name=tag_name, exclusive=True)
            print(f"Fixed: '{tag_name}' is now set as an exclusive tag")
        except:
            print(f"Tag '{tag_name}' already exists, updating all but one entity")
            
            # Keep only the most recent entity tagged
            for entity in tagged_entities[1:]:
                from zenml.utils.tag_utils import remove_tags
                if entity_type == "pipeline":
                    remove_tags(tags=[tag_name], pipeline=entity.id)
                elif entity_type == "model":
                    remove_tags(tags=[tag_name], model_name=entity.name, model_version=entity.version)
```

## Conclusion and Next Steps

You've now learned how to implement a comprehensive organization strategy in ZenML. By combining tags and projects, you can:

1. Keep your ML assets organized and discoverable
2. Track model lineage and performance
3. Manage environments from development to production
4. Support multi-team collaboration

For more advanced techniques, consider:

1. Automating tagging through CI/CD pipelines
2. Creating organization dashboards with your tagging system
3. Implementing governance processes for tag management

## Next Steps

Now that you understand how to organize your ML assets, explore:

1. [Managing scheduled pipelines](managing-scheduled-pipelines-v2.md) to automate your ML workflows
2. Creating custom visualizations based on your tagging system
3. Implementing automated promotion workflows using exclusive tags
