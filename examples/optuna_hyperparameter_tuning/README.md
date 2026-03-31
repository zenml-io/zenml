# Hyperparameter Tuning with Optuna + ZenML

A production-ready example demonstrating intelligent hyperparameter optimization using **Optuna's ask API** combined with **ZenML dynamic pipelines** for parallel trial execution. Trains a CNN on FashionMNIST using PyTorch Lightning, with parallel trial execution and full metadata tracking in the ZenML dashboard.

## What This Demonstrates

- **Optuna integration**: Use Optuna's ask API for intelligent hyperparameter sampling
- **Dynamic pipelines**: Fan out trials in parallel using `step.map()`
- **Resource management**: Efficient parallel execution with configurable resource pools
- **Metadata tracking**: Every trial's metrics are logged and queryable via the ZenML dashboard and MCP server
- **Two optimization patterns**: Simple parallel sweep vs. adaptive multi-round optimization

## Architecture

```
Optuna Study (In-Memory)
    |
    +-> Ask API: Generate trial configs
    |       |
    |       +-> ZenML Pipeline: Orchestrate parallel training
    |       |       |
    |       |       +-- train_trial_0 --+
    |       |       +-- train_trial_1   +-- Parallel execution
    |       |       +-- train_trial_2   |   (managed by orchestrator)
    |       |       +-- train_trial_N --+
    |       |               |
    |       +---------------+-> Collect results
    |
    +-> Artifact History: Results flow through ZenML artifacts (no shared DB needed)
```

**Key insight**: Optuna decides *what* to try next (smart sampling). ZenML decides *where* and *when* to run it (orchestration, parallelism, caching). Trial history flows through ZenML artifacts, so this works on any orchestrator -- local or distributed.

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

### Run the Simple Sweep

All trials run in parallel:

```bash
python run.py
# ^^^This uses `config/simple.yaml` by default -- 2 trials in parallel, 3 training epochs each. To customize:
# or specify explicitly:
python run.py simple
python run.py simple --config config/my_experiment.yaml  # your own config
```

### Run the Adaptive Sweep

Multiple rounds where each round learns from the previous:

```bash
python run.py adaptive
python run.py adaptive --config config/my_experiment.yaml  # your own config
```

This uses `config/adaptive.yaml` by default -- 2 rounds of 2 trials each (4 trials total), 3 epochs per trial. Optuna's TPE sampler uses early results to suggest better hyperparameters in later rounds.

### Configuration

Each mode has its own YAML config file with pipeline parameters, feature flags, and Docker settings:

- `config/simple.yaml` -- parameters for `sweep_pipeline` (`n_trials`, `max_iter`, ...)
- `config/adaptive.yaml` -- parameters for `adaptive_sweep_pipeline` (`n_rounds`, `trials_per_round`, `max_iter`, ...)

These are standard [ZenML YAML config files](https://docs.zenml.io/concepts/steps_and_pipelines/yaml_configuration). Edit them to change trial counts, training epochs, caching behavior, or Docker settings for remote execution.

## What You'll See in the Dashboard

### Simple Sweep DAG

```
suggest_trials (generates 5 configs)
     |
     +-- train_trial_0 --+
     +-- train_trial_1   |
     +-- train_trial_2   +-- All run in parallel
     +-- train_trial_3   |   (managed by orchestrator)
     +-- train_trial_4 --+
             |
        report_results (aggregates metrics, finds best)
             |
        retrain_best_model (saves production model)
```

**Key insight**: Trial models are discarded (only metrics saved). After finding the best hyperparameters, the pipeline retrains with those params and saves only that production-ready model.

### Adaptive Sweep DAG

```
Round 1:
  suggest_trials_round_0
       +-- train_trial_0, 1 (parallel)
       +-- report_results_round_0

Round 2:
  suggest_trials_round_1 (learns from round 1)
       +-- train_trial_2, 3 (parallel)
       +-- report_results_round_1

Round 3:
  suggest_trials_round_2 (learns from rounds 1 & 2)
       +-- train_trial_4, 5 (parallel)
       +-- report_results_round_2
            |
       retrain_best_model (saves production model)
```

### Metadata & Artifacts

Each trial artifact has rich metadata attached:

```python
{
    "trial_number": 3,
    "val_loss": 0.4321,
    "val_accuracy": 84.52,
    "learning_rate": 0.003421,
    "batch_size": 64,
    "hidden_dim": 32,
    "n_epochs": 10,
}
```

This makes trials **queryable**:
- Via dashboard: filter/sort by val_loss, learning_rate, etc.
- Via MCP server: "show me all trials with val_loss < 0.4"
- Via ZenML client: `client.list_artifact_versions()` with metadata filters

## How It Works

### 1. Suggest Trials (`steps/suggest.py`)

Optuna's **ask API** generates trial configurations. An in-memory study is created and seeded with results from previous rounds (if any) via ZenML artifacts:

```python
study = optuna.create_study(study_name=study_name, direction="minimize")

# Replay previous results so the TPE sampler learns from them
if previous_summary and previous_summary.get("all_trials"):
    for trial_info in previous_summary["all_trials"]:
        study.add_trial(optuna.trial.create_trial(...))

# Generate new trial configs
for _ in range(n_trials):
    trial = study.ask()
    config = {
        "trial_number": trial.number,
        "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [64, 128]),
        "hidden_dim": trial.suggest_categorical("hidden_dim", [8, 16, 32]),
    }
    trials.append(config)
```

Returns a list of configs, one per trial.

### 2. Train in Parallel (`steps/train.py`)

Each trial trains a CNN independently using PyTorch Lightning:

```python
@step
def train_trial(trial_config: dict, max_iter: int = 10) -> dict:
    model = FashionMNISTClassifier(
        learning_rate=trial_config["learning_rate"],
        hidden_dim=trial_config["hidden_dim"],
    )

    trainer = Trainer(max_epochs=max_iter, callbacks=[EarlyStopping(...)])
    trainer.fit(model, train_loader, val_loader)

    log_metadata({
        "trial_number": trial_config["trial_number"],
        "val_loss": val_loss,
        "learning_rate": trial_config["learning_rate"],
        ...
    })

    return {"trial_number": ..., "val_loss": val_loss, ...}
```

### 3. Report Results (`steps/report.py`)

Aggregates trial results and finds the best configuration. Results from all rounds are accumulated through ZenML artifacts:

```python
@step
def report_results(results: list, previous_summary: dict = None) -> dict:
    all_trials = previous_summary.get("all_trials", []) + current_results
    best = min(all_trials, key=lambda t: t["val_loss"])
    return {"best_val_loss": best["val_loss"], "best_params": ..., "all_trials": all_trials}
```

### 4. Retrain Best Model (`steps/save_best.py`)

After finding the best hyperparameters, retrain with more epochs for production:

```python
@step
def retrain_best_model(sweep_summary: dict, max_iter: int = 20) -> model:
    best_params = sweep_summary["best_params"]

    model = FashionMNISTClassifier(
        learning_rate=best_params["learning_rate"],
        hidden_dim=best_params["hidden_dim"],
    )
    trainer = Trainer(max_epochs=max_iter, callbacks=[EarlyStopping(...)])
    trainer.fit(model, train_loader, val_loader)

    log_metadata(metadata={...}, infer_artifact=True)
    return model  # Saved as ZenML artifact
```

**Why this approach?**
- **No storage waste**: Trial models discarded (only metrics saved)
- **Production-ready**: Best model gets extra training (200 vs 10 epochs)
- **Queryable**: Model metadata logged for dashboard/MCP queries
- **Reproducible**: Hyperparameters logged, can retrain anytime

### 5. Dynamic Pipeline Orchestration

The pipeline uses `.map()` to fan out trials:

```python
@pipeline(dynamic=True)
def sweep_pipeline(...):
    trials = suggest_trials(...)           # List[dict]
    results = train_trial.map(             # .map() fans out in parallel
        trial_config=trials
    )
    report_results(..., results=results)   # Reducer step
```

ZenML handles:
- Parallel execution (all trials at once, or queued by resource pools)
- Artifact tracking (each trial's inputs/outputs are versioned)
- Caching (re-run with same params? Cached results are reused)
- Metadata (every trial's metrics are queryable)

## Two Optimization Patterns

### Pattern 1: Simple Parallel Sweep

**When to use**: Small-scale sweeps where you want maximum parallelism.

```python
sweep_pipeline(n_trials=10)
```

- All 10 trials suggested upfront
- All 10 train in parallel (or queued by resource availability)
- Best for: Grid search, small random search, quick experiments

### Pattern 2: Adaptive Multi-Round Sweep

**When to use**: Larger search spaces where you want Optuna's smart sampling to learn from early trials.

```python
adaptive_sweep_pipeline(n_rounds=5, trials_per_round=4)
```

- Round 1: Suggest 4 trials, train, report
- Round 2: Optuna uses round 1 results to suggest better trials
- Round 3+: Continues refining based on all previous results
- Best for: Bayesian optimization, large search spaces, sample efficiency

## Customizing the Search Space

Edit the `SEARCH_SPACE` constant in `steps/suggest.py`:

```python
SEARCH_SPACE = {
    "learning_rate": {"low": 1e-5, "high": 1e-1, "log": True},
    "batch_size": {"choices": [32, 64, 128, 256]},
    "hidden_dim": {"choices": [16, 32, 64, 128]},
}
```

## Remote Execution & Production Deployment

### Portable Architecture

This example uses **in-memory Optuna studies** seeded from ZenML artifact history. This means:
- No shared database required between containers
- Works on any orchestrator (local, Kubernetes, cloud)
- Trial history is preserved across rounds through ZenML artifacts

### Resource Pools

When you configure resource pools in ZenML, the pipeline automatically manages parallel execution across available resources. No code changes needed. The same `train_trial` step works locally and in production environments.

## Project Structure

```
examples/optuna_hyperparameter_tuning/
+-- README.md                    # This file
+-- requirements.txt             # Dependencies (optuna, torch)
+-- run.py                       # Entry point (simple/adaptive modes)
+-- config/
|   +-- simple.yaml              # Config for sweep_pipeline
|   +-- adaptive.yaml            # Config for adaptive_sweep_pipeline
+-- pipelines/
|   +-- __init__.py
|   +-- sweep.py                 # sweep_pipeline + adaptive_sweep_pipeline
+-- steps/
    +-- __init__.py
    +-- model.py                 # Shared FashionMNISTClassifier definition
    +-- data.py                  # Shared FashionMNIST data loading
    +-- suggest.py               # Optuna ask API + trial suggestion
    +-- train.py                 # Single trial training (PyTorch Lightning)
    +-- save_best.py             # Retrain best model for production
    +-- report.py                # Results aggregation + summary
```

## Troubleshooting

### `CategoricalDistribution does not support dynamic value space`

This can happen if you modified the search space choices between runs. Since studies are in-memory and seeded from artifact history, changing the choices while previous artifacts still exist can cause conflicts.

**Fix**: Start a new study by changing `study_name` in your config YAML file.

## Further Reading

- **ZenML Dynamic Pipelines**: [docs.zenml.io/how-to/dynamic-pipelines](https://docs.zenml.io/how-to/dynamic-pipelines)
- **Hyperparameter Tuning Guide**: [docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning](https://docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning)
- **Resource Pools**: [docs.zenml.io/how-to/resource-pools](https://docs.zenml.io/how-to/resource-pools)
- **Optuna Documentation**: [optuna.readthedocs.io](https://optuna.readthedocs.io)

## Need Help?

- **ZenML Slack**: [zenml.io/slack](https://zenml.io/slack)
- **GitHub Issues**: [github.com/zenml-io/zenml/issues](https://github.com/zenml-io/zenml/issues)
- **Docs**: [docs.zenml.io](https://docs.zenml.io)
