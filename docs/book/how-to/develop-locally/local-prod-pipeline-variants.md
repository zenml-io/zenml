---
description: Create different variants of your pipeline for local development and production.
---

# Create pipeline variants for local development and production

When developing ZenML pipelines, it's often beneficial to have different variants of your pipeline for local development and production environments. This approach allows you to iterate quickly during development while maintaining a full-scale setup for production. While configuration files are one way to achieve this, you can also implement this directly in your code.

There are several ways to create different variants of your pipeline:

1. Using configuration files
2. Implementing variants in code
3. Using environment variables

Let's explore each of these methods:

## Using configuration files

ZenML allows you to specify pipeline and step configurations using YAML files. Here's an example:

```yaml
enable_cache: False
parameters:
    dataset_name: "small_dataset"
steps:
    load_data:
        enable_cache: False
```

This config file sets up a development variant by using a smaller dataset and disabling caching.

To apply this configuration to your pipeline, use the `with_options(config_path=<PATH_TO_CONFIG>)` pattern:

```python
from zenml import step, pipeline

@step
def load_data(dataset_name: str) -> dict:
    ...

@pipeline
def ml_pipeline(dataset_name: str):
    load_data(dataset_name)

if __name__ == "__main__":
    ml_pipeline.with_options(config_path="path/to/config.yaml")()
```

You can create separate configuration files for development and production:

- `config_dev.yaml`: Configuration for local development
- `config_prod.yaml`: Configuration for production

## Implementing variants in code

You can also create pipeline variants directly in your code:

```python
import os
from zenml import step, pipeline

@step
def load_data(dataset_name: str) -> dict:
    # Load data based on the dataset name
    ...

@pipeline
def ml_pipeline(is_dev: bool = False):
    dataset = "small_dataset" if is_dev else "full_dataset"
    load_data(dataset)

if __name__ == "__main__":
    is_dev = os.environ.get("ZENML_ENVIRONMENT") == "dev"
    ml_pipeline(is_dev=is_dev)
```

This approach allows you to switch between development and production variants using a simple boolean flag.

## Using environment variables

You can use environment variables to determine which variant to run:

```python
import os

if os.environ.get("ZENML_ENVIRONMENT") == "dev":
    config_path = "config_dev.yaml"
else:
    config_path = "config_prod.yaml"

ml_pipeline.with_options(config_path=config_path)()
```

Run your pipeline with: `ZENML_ENVIRONMENT=dev python run.py` or `ZENML_ENVIRONMENT=prod python run.py`.

## Development variant considerations

When creating a development variant of your pipeline, consider optimizing these
aspects for faster iteration and debugging:

- Use smaller datasets for quicker runs
- Specify a local stack for execution
- Reduce number of training epochs
- Decrease batch size
- Use a smaller base model

For example, in a configuration file:

```yaml
parameters:
    dataset_path: "data/small_dataset.csv"
epochs: 1
batch_size: 16
stack: local_stack
```

Or in code:

```python
@pipeline
def ml_pipeline(is_dev: bool = False):
    dataset = "data/small_dataset.csv" if is_dev else "data/full_dataset.csv"
    epochs = 1 if is_dev else 100
    batch_size = 16 if is_dev else 64
    
    load_data(dataset)
    train_model(epochs=epochs, batch_size=batch_size)
```

By creating different variants of your pipeline, you can quickly test and debug
your code locally with a lightweight setup, while maintaining a full-scale
configuration for production execution. This approach streamlines your
development workflow and allows for efficient iteration without compromising
your production pipeline.
