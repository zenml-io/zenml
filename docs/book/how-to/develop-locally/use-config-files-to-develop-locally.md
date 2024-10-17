---
description: Learn how to use configuration files to manage local development.
---

# Use configuration files for local development

Configuration files allow you to easily manage and customize your ZenML pipelines for different environments, such as local development vs remote execution. By using YAML config files, you can separate the configuration from your code and easily switch between different setups.

## YAML config files for local and remote development

ZenML allows you to specify pipeline and step configurations using YAML files. Here's a simple example:

```yaml
enable_cache: False
parameters:
    dataset_name: "best_dataset"
steps:
    load_data:
        enable_cache: False
```

This config file disables caching for the pipeline and the `load_data` step, and sets the `dataset_name` parameter to `"best_dataset"`.

To apply this configuration to your pipeline, use the `with_options(config_path=<PATH_TO_CONFIG>)` pattern:

```python
from zenml import step, pipeline

@step
def load_data(dataset_name: str) -> dict:
    ...

@pipeline
def simple_ml_pipeline(dataset_name: str):
    load_data(dataset_name)

if __name__ == "__main__":
    simple_ml_pipeline.with_options(config_path="path/to/config.yaml")()
```

For more details on what can be configured in the YAML file, refer to the [full configuration documentation](https://docs.zenml.io/how-to/use-configuration-files/what-can-be-configured).

To manage configurations for local development vs remote execution, you can create two separate YAML files, one for each environment. For example:

- `config_local.yaml`: Configuration for local development 
- `config_remote.yaml`: Configuration for remote execution

Then in your `run.py` script, you can choose which config file to use based on a flag or environment variable:

```python
import os

if os.environ.get("ENVIRONMENT") == "local":
    config_path = "config_local.yaml"
else:
    config_path = "config_remote.yaml"

simple_ml_pipeline.with_options(config_path=config_path)()
```

And then you could run this with `ENVIRONMENT=local python run.py` or
`ENVIRONMENT=remote python run.py`. (Alternatively, you could use a CLI flag
with `argparse` or `click` instead of an environment variable.)


## Development environment configuration

In your local development config file, you can customize various settings to optimize for faster iteration and debugging. Some things you might want to configure:

- Use smaller datasets for quicker runs
- Specify a local stack for execution
- Reduce number of training epochs
- Decrease batch size
- Use a smaller base model

For example:

```yaml
parameters:
    dataset_path: "data/small_dataset.csv"
epochs: 1
batch_size: 16
stack: local_stack
```

This allows you to quickly test and debug your code locally before running it with the full-scale configuration for remote execution.
By leveraging configuration files, you can easily manage different setups for
your ZenML pipelines and streamline your development workflow.
