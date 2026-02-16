---
description: Running a hyperparameter tuning trial with ZenML.
icon: itunes-note
---

# Hyper-parameter tuning

## Introduction

Hyperparameter tuning is the process of systematically searching for the best set of hyperparameters for your model. ZenML serves as the orchestration layer that works with any optimization library you choose — whether that's Optuna, Ray Tune, Ax, or simple grid search. You bring the sampling algorithm, ZenML handles execution, parallelism, tracking, and caching.

In this tutorial you will:

1. Start with a simple grid search pattern (good for beginners)
2. Progress to advanced optimization using Optuna + dynamic pipelines
3. Learn how to combine ZenML with Hydra for configuration management
4. Understand how to scale hyperparameter sweeps with parallel execution

### Prerequisites

* ZenML installed and an active stack (the local default stack is fine)
* `scikit-learn` installed (`pip install scikit-learn`)
* Basic familiarity with ZenML pipelines and steps

---

## Simple Grid Search (Basic Pattern)

For simple cases, you can implement a basic grid search using a for loop in your pipeline. This is a good starting point to understand the fundamentals before moving to more advanced patterns.

### Step 1: Define the training step

Create a training step that accepts the learning rate as an input parameter and returns the trained model:

```python
from typing import Annotated
from sklearn.base import ClassifierMixin
from zenml import step

MODEL_OUTPUT = "model"

@step
def train_step(learning_rate: float) -> Annotated[ClassifierMixin, MODEL_OUTPUT]:
    """Train a model with the given learning rate."""
    # <your training code goes here>
    ...
```

### Step 2: Create a fan-out / fan-in pipeline

Wire several instances of the same `train_step` into a pipeline, each with a different hyperparameter. Then use a selection step that picks the best model:

```python
from zenml import pipeline
from zenml import get_step_context, step
from zenml.client import Client

@step
def selection_step(step_prefix: str, output_name: str):
    """Pick the best model among all training steps."""
    run = Client().get_pipeline_run(get_step_context().pipeline_run.name)
    trained_models = {}
    for step_name, step_info in run.steps.items():
        if step_name.startswith(step_prefix):
            model = step_info.outputs[output_name][0].load()
            lr = step_info.config.parameters["learning_rate"]
            trained_models[lr] = model

    # <evaluate and select your favorite model here>

@pipeline
def hp_tuning_pipeline(step_count: int = 4):
    after = []
    for i in range(step_count):
        train_step(learning_rate=i * 0.0001, id=f"train_step_{i}")
        after.append(f"train_step_{i}")

    selection_step(step_prefix="train_step_", output_name=MODEL_OUTPUT, after=after)
```

### Step 3: Run the pipeline

```python
if __name__ == "__main__":
    hp_tuning_pipeline(step_count=4)()
```

While the pipeline is running you can follow the logs in your terminal or open the ZenML dashboard and watch the DAG execute.

### Step 4: Inspect results

Once the run is finished you can programmatically analyze which hyperparameter performed best or load the chosen model:

```python
from zenml.client import Client

run = Client().get_pipeline("hp_tuning_pipeline").last_run
best_model = run.steps["selection_step"].outputs["best_model"].load()
```

For a deeper exploration of how to query past pipeline runs, see the [Inspecting past pipeline runs](fetching-pipelines.md) tutorial.

{% hint style="info" %}
The basic pattern shown above works well for simple cases. For more advanced hyperparameter optimization with parallel execution and intelligent sampling, see the sections below.
{% endhint %}

---

## Advanced: Optuna + Dynamic Pipelines

For production-grade hyperparameter optimization, ZenML's dynamic pipelines with `.map()` enable intelligent sampling and parallel execution. This pattern works with any optimization library (Optuna, Ray Tune, Ax, etc.) — the key is separating concerns: your library handles sampling strategy, ZenML handles orchestration.

### Key Concepts

Dynamic pipelines allow you to:
- Use `@pipeline(dynamic=True)` to enable runtime pipeline construction
- Fan out trials in parallel with `step.map()`
- Use Optuna's ask/tell API for intelligent hyperparameter sampling
- Track trial metadata with `log_metadata()` for easy comparison

### Minimal Example Pattern

Here's the essential pattern (see the [full optuna_sweep example](https://github.com/zenml-io/zenml/tree/main/examples/optuna_sweep) for complete code):

```python
from zenml import pipeline, step, log_metadata
from typing import List, Dict, Any, Annotated

@step
def suggest_trials(
    study_name: str,
    storage_url: str,
    n_trials: int = 5
) -> Annotated[List[Dict[str, Any]], "trial_configs"]:
    """Generate trial configurations using Optuna's ask API."""
    import optuna

    study = optuna.create_study(
        study_name=study_name,
        storage=storage_url,
        load_if_exists=True,
        direction="minimize"
    )

    trial_configs = []
    for _ in range(n_trials):
        trial = study.ask()
        config = {
            "trial_number": trial.number,
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-1, log=True),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e-1, log=True),
            # ... other hyperparameters
        }
        trial_configs.append(config)

    return trial_configs

@step
def train_trial(
    trial_config: Dict[str, Any]
) -> Annotated[Dict[str, Any], "trial_result"]:
    """Train a single trial with given hyperparameters."""
    # Extract hyperparameters from config
    learning_rate = trial_config["learning_rate"]
    alpha = trial_config["alpha"]

    # Train your model
    model = train_model(learning_rate, alpha)
    val_loss = evaluate_model(model)

    # Prepare result
    result = {
        "trial_number": trial_config["trial_number"],
        "val_loss": val_loss,
        "learning_rate": learning_rate,
        "alpha": alpha,
    }

    # Log metadata for easy querying and visualization
    log_metadata(
        metadata={
            "trial_number": trial_config["trial_number"],
            "val_loss": val_loss,
            "learning_rate": learning_rate,
            "alpha": alpha,
        },
        artifact_name="trial_result"
    )

    return result

@step
def report_results(
    study_name: str,
    storage_url: str,
    results: List[Dict[str, Any]]
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Report results back to Optuna using tell API."""
    import optuna

    study = optuna.load_study(study_name=study_name, storage=storage_url)

    for result in results:
        # Get the trial object and report the result
        trial_number = result["trial_number"]
        trial = study._storage.get_trial(study._study_id, trial_number)
        study.tell(trial, result["val_loss"])

    # Return summary of best trial
    best_trial = study.best_trial
    return {
        "best_trial_number": best_trial.number,
        "best_val_loss": best_trial.value,
        "best_params": best_trial.params,
    }

@pipeline(dynamic=True, enable_cache=True)
def sweep_pipeline(
    study_name: str = "my_sweep",
    storage_url: str = "sqlite:///optuna.db",
    n_trials: int = 5
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Parallel hyperparameter sweep using Optuna + ZenML."""
    # Generate trial configurations
    trials = suggest_trials(
        study_name=study_name,
        storage_url=storage_url,
        n_trials=n_trials
    )

    # Fan out: train all trials in parallel using .map()
    results = train_trial.map(trial_config=trials)

    # Reduce: report results back to Optuna
    summary = report_results(
        study_name=study_name,
        storage_url=storage_url,
        results=results
    )

    return summary
```

### How It Works

1. **Suggest**: Optuna's ask API generates N trial configurations
2. **Fan-out**: `.map()` creates N parallel training steps, one per trial
3. **Train**: Each trial trains independently with its hyperparameters
4. **Track**: `log_metadata()` makes trials queryable in the dashboard
5. **Reduce**: Report all results back to Optuna's tell API

### Adaptive Multi-Round Optimization

For even better sample efficiency, run multiple rounds where later trials learn from earlier ones:

```python
@pipeline(dynamic=True, enable_cache=True)
def adaptive_sweep_pipeline(
    study_name: str = "adaptive_sweep",
    storage_url: str = "sqlite:///optuna.db",
    n_rounds: int = 3,
    trials_per_round: int = 3
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Multi-round sweep where Optuna learns between rounds."""
    summary = None

    for round_idx in range(n_rounds):
        # Generate trials based on previous results
        trials = suggest_trials.with_options(id=f"suggest_trials_round_{round_idx}")(
            study_name=study_name,
            storage_url=storage_url,
            n_trials=trials_per_round
        )

        # Train trials in parallel
        results = train_trial.map(trial_config=trials)

        # Report results (informs next round's suggestions)
        summary = report_results.with_options(id=f"report_results_round_{round_idx}")(
            study_name=study_name,
            storage_url=storage_url,
            results=results
        )

    return summary
```

This pattern allows Optuna's Bayesian samplers (TPE, CMA-ES, etc.) to refine their search strategy between rounds.

### Complete Example

For a complete working example with FashionMNIST classification, see:
- [examples/optuna_sweep/](https://github.com/zenml-io/zenml/tree/main/examples/optuna_sweep)

The example includes:
- Full Optuna integration with persistent storage
- Resource settings for parallel execution
- Metadata logging for trial visualization
- Both simple and adaptive sweep patterns

---

## Combining with Hydra

For complex experiments, you can use Hydra for configuration management while ZenML handles orchestration. This separation of concerns keeps your codebase clean: Hydra decides WHAT to optimize (search space, architecture), ZenML decides WHERE and WHEN (orchestration, GPU scheduling).

### Basic Pattern

```python
from hydra import compose, initialize
from omegaconf import OmegaConf

def main():
    # Initialize Hydra and load configuration
    initialize(config_path="conf", version_base=None)
    cfg = compose(config_name="config")

    # Convert to plain dict for ZenML
    config = OmegaConf.to_container(cfg, resolve=True)

    # Run ZenML pipeline with Hydra-resolved config
    sweep_pipeline(
        study_name=config["sweep"]["study_name"],
        n_trials=config["sweep"]["n_trials"],
        search_space=config["search_space"]
    )
```

Your Hydra config (`conf/config.yaml`) might look like:

```yaml
sweep:
  study_name: fashion_mnist_sweep
  n_trials: 10
  max_iter: 50

search_space:
  learning_rate_init:
    low: 0.0001
    high: 0.1
    log: true
  alpha:
    low: 0.00001
    high: 0.1
    log: true
  hidden_layer_sizes:
    choices: [[64], [128], [64, 32], [128, 64]]
```

This allows easy overrides from the command line:

```bash
python run_hydra.py sweep.n_trials=20 sweep.max_iter=100
```

For a complete example, see [examples/optuna_sweep/run_hydra.py](https://github.com/zenml-io/zenml/tree/main/examples/optuna_sweep).

---

## Next Steps

* **Scale with resource pools**: Configure parallel execution across multiple GPUs or machines using [resource pools](https://docs.zenml.io/stacks/stack-components/step-operators)
* **Learn dynamic pipelines**: Explore more fan-out patterns in the [dynamic pipelines documentation](https://docs.zenml.io/user-guide/advanced-guide/pipelining-features/dynamic-pipelines)
* **Try the full example**: Clone and run [examples/optuna_sweep/](https://github.com/zenml-io/zenml/tree/main/examples/optuna_sweep) to see everything working together
* **Other optimization libraries**: The same patterns work with Ray Tune, Ax, or any library that supports ask/tell style optimization
* **Deploy winning models**: Use [Pipeline Deployments](https://docs.zenml.io/concepts/deployment) to serve your best model as an HTTP endpoint
* **Remote orchestration**: Move to a [remote orchestrator](https://docs.zenml.io/stacks/orchestrators) to scale out your search to a Kubernetes cluster or cloud VMs
