# Configuration Management with Hydra + ZenML

An example demonstrating how to use **Hydra** for configuration management alongside **ZenML** for ML pipeline orchestration. Trains a CNN on FashionMNIST using PyTorch Lightning, with all hyperparameters and settings managed through Hydra's composable config system.

## What This Demonstrates

- **Hydra config composition**: Manage training hyperparameters, model settings, and data config from YAML
- **CLI overrides**: Change any parameter from the command line without editing code
- **Separation of concerns**: Hydra decides WHAT (hyperparameters, architecture), ZenML decides WHERE/WHEN (orchestration, caching, artifacts)
- **ZenML pipeline settings**: Pass Docker settings, cache control, and resource configs through Hydra
- **Metadata tracking**: Training metrics logged and queryable via the ZenML dashboard

## Architecture

```
Hydra (conf/config.yaml + CLI overrides)
    |
    +-> Resolves all configuration
    |       |
    |       +-> training: learning_rate, batch_size, hidden_dim, max_epochs
    |       +-> model: architecture, num_classes
    |       +-> data: dataset, seed, splits
    |       +-> zenml_config: caching, docker settings
    |
    +-> Passes resolved config to ZenML pipeline
            |
            +-> train_model (trains CNN with Hydra-configured params)
            |       |
            +-> evaluate_model (evaluates on validation set)
```

**Key insight**: Hydra handles all configuration (composable YAML, CLI overrides, type safety). ZenML handles all orchestration (scheduling, caching, artifact versioning, metadata). Neither needs to know about the other's internals.

## Quick Start

### Prerequisites

```bash
uv venv --seed
source .venv/bin/activate
pip install -r requirements.txt
zenml init
zenml login
```

If you have an AWS Kubernetes-based stack, also install the required ZenML integrations:

```bash
zenml integration install aws s3 kubernetes --yes --uv
```

### Run with Defaults

```bash
python run.py
```

This trains a CNN on FashionMNIST using the defaults from `conf/config.yaml` (learning_rate=0.001, batch_size=64, hidden_dim=32, max_epochs=10).

### Override from CLI

Hydra lets you override any config value from the command line:

```bash
# Override learning rate
python run.py training.learning_rate=0.005

# Override multiple parameters
python run.py training.max_epochs=50 training.hidden_dim=64

# Larger model with more training
python run.py training.hidden_dim=128 training.batch_size=128 training.max_epochs=100

# Disable ZenML caching
python run.py zenml_config.enable_cache=false
```

## Configuration Structure

All configuration lives in `conf/config.yaml`:

```yaml
# Training hyperparameters
training:
  learning_rate: 0.001
  batch_size: 64
  hidden_dim: 32
  max_epochs: 10

# Model configuration
model:
  architecture: CNN
  num_classes: 10
  framework: PyTorch Lightning

# Data configuration
data:
  dataset: FashionMNIST
  train_split: 0.8
  val_split: 0.2
  seed: 42

# ZenML pipeline configuration
zenml_config:
  enable_cache: true
  settings:
    docker:
      requirements: "requirements.txt"
```

### Why Hydra?

- **Single source of truth**: All parameters in one place
- **CLI overrides**: Quick experiments without code changes
- **Type safety**: Hydra validates config structure
- **Composability**: Hydra supports config groups, defaults lists, and multirun for advanced use cases
- **Reproducibility**: The resolved config is logged, so you always know what ran

## What You'll See in the Dashboard

### Pipeline DAG

```
train_model (trains CNN with configured hyperparameters)
     |
evaluate_model (validates model, reports per-class accuracy)
```

### Metadata

The trained model artifact has metadata attached:

```python
{
    "val_loss": 0.4321,
    "val_accuracy": 84.52,
    "train_accuracy": 89.10,
    "learning_rate": 0.001,
    "batch_size": 64,
    "hidden_dim": 32,
    "n_epochs": 10,
    "max_epochs": 10,
    "converged": false,
}
```

The evaluation results include per-class accuracy:

```python
{
    "val_loss": 0.4321,
    "val_accuracy": 84.52,
    "per_class_accuracy": {
        "T-shirt/top": 82.3,
        "Trouser": 96.1,
        "Pullover": 78.5,
        ...
    }
}
```

## How It Works

### 1. Hydra Resolves Configuration (`run.py`)

```python
with initialize(config_path="conf", version_base=None):
    cfg = compose(config_name="config", overrides=sys.argv[1:])

config = OmegaConf.to_container(cfg, resolve=True)
```

Hydra loads `conf/config.yaml`, applies any CLI overrides, and produces a plain Python dict.

### 2. ZenML Pipeline Receives Config (`pipelines/training.py`)

```python
@pipeline
def training_pipeline(
    learning_rate: float = 0.001,
    batch_size: int = 64,
    hidden_dim: int = 32,
    max_epochs: int = 10,
) -> None:
    model = train_model(
        learning_rate=learning_rate,
        batch_size=batch_size,
        hidden_dim=hidden_dim,
        max_epochs=max_epochs,
    )
    evaluate_model(model=model, batch_size=batch_size)
```

The pipeline parameters come directly from the Hydra-resolved config. ZenML handles caching, artifact tracking, and orchestration.

### 3. Train Model (`steps/train.py`)

Trains the CNN with the configured hyperparameters. The model is saved as a ZenML artifact with metadata logged for dashboard queries.

### 4. Evaluate Model (`steps/evaluate.py`)

Runs the trained model through the validation set, computing overall accuracy and per-class accuracy for all 10 FashionMNIST classes.

## Separation of Concerns

| Concern | Handled By | Example |
|---------|-----------|---------|
| Hyperparameters | Hydra | `training.learning_rate=0.005` |
| Model architecture | Hydra | `training.hidden_dim=128` |
| Data configuration | Hydra | `data.seed=123` |
| Docker settings | Hydra | `zenml_config.settings.docker.requirements=...` |
| Pipeline orchestration | ZenML | Scheduling, parallelism, retries |
| Artifact versioning | ZenML | Automatic model/data versioning |
| Caching | ZenML | Skip unchanged steps |
| Metadata tracking | ZenML | Dashboard queries, MCP server |

## Project Structure

```
examples/hydra_config_management/
+-- README.md                    # This file
+-- requirements.txt             # Dependencies (hydra, torch)
+-- run.py                       # Entry point (Hydra config + ZenML pipeline)
+-- conf/
|   +-- config.yaml              # Hydra configuration
+-- pipelines/
|   +-- __init__.py
|   +-- training.py              # training_pipeline
+-- steps/
    +-- __init__.py
    +-- model.py                 # Shared FashionMNISTClassifier definition
    +-- data.py                  # Shared FashionMNIST data loading
    +-- train.py                 # Model training step
    +-- evaluate.py              # Model evaluation step
```

## Further Reading

- **Hydra Documentation**: [hydra.cc](https://hydra.cc)
- **ZenML Pipelines**: [docs.zenml.io/how-to/build-pipelines](https://docs.zenml.io/how-to/build-pipelines)
- **ZenML Metadata**: [docs.zenml.io/how-to/metadata](https://docs.zenml.io/how-to/metadata)

## Need Help?

- **ZenML Slack**: [zenml.io/slack](https://zenml.io/slack)
- **GitHub Issues**: [github.com/zenml-io/zenml/issues](https://github.com/zenml-io/zenml/issues)
- **Docs**: [docs.zenml.io](https://docs.zenml.io)
