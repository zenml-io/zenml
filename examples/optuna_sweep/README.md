# Hyperparameter Sweeps with Optuna + ZenML Dynamic Pipelines

A production-ready example demonstrating intelligent hyperparameter optimization using **Optuna's ask API** combined with **ZenML dynamic pipelines** for parallel trial execution. Trains a CNN on FashionMNIST using PyTorch Lightning, with parallel trial execution and full metadata tracking in the ZenML dashboard.

## What This Demonstrates

- **Optuna integration**: Use Optuna's ask API for intelligent hyperparameter sampling
- **Dynamic pipelines**: Fan out trials in parallel using `step.map()`
- **Resource management**: Efficient parallel execution with configurable resource pools
- **Metadata tracking**: Every trial's metrics are logged and queryable via the ZenML dashboard and MCP server
- **Two optimization patterns**: Simple parallel sweep vs. adaptive multi-round optimization
- **Hydra integration**: Optional config composition for complex search spaces

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
pip install -r requirements.txt
zenml init
zenml login
```

### Run the Simple Sweep

All trials run in parallel:

```bash
python run.py
# or explicitly:
python run.py simple
```

This runs 5 trials in parallel, training a CNN on FashionMNIST with different hyperparameters (learning rate, batch size, hidden dimension). Training runs for up to 10 epochs per trial.

### Run the Adaptive Sweep

Multiple rounds where each round learns from the previous:

```bash
python run.py adaptive
```

This runs 3 rounds of 2 trials each (6 trials total), with 10 training epochs per trial. Optuna's TPE sampler uses early results to suggest better hyperparameters in later rounds.

### Run with Hydra Configuration

Manage complex search spaces and configuration with Hydra:

```bash
pip install hydra-core omegaconf

# Simple mode (default from conf/config.yaml)
python run_hydra.py

# Adaptive mode
python run_hydra.py sweep.mode=adaptive

# Override from CLI
python run_hydra.py sweep.n_trials=10                            # More trials (simple mode)
python run_hydra.py sweep.mode=adaptive sweep.n_rounds=5         # Adaptive with 5 rounds
python run_hydra.py search_space.learning_rate.high=0.5          # Override search space
python run_hydra.py sweep.max_iter=50 sweep.n_trials=20          # Multiple overrides
```

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

    # Log metadata for dashboard/MCP queries
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

## Remote Execution & Production Deployment

### Portable Architecture

This example uses **in-memory Optuna studies** seeded from ZenML artifact history. This means:
- No shared database required between containers
- Works on any orchestrator (local, Kubernetes, cloud)
- Trial history is preserved across rounds through ZenML artifacts

### Resource Pools

When you configure resource pools in ZenML, the pipeline automatically manages parallel execution across available resources. No code changes needed. The same `train_trial` step works locally and in production environments.

## Hydra + ZenML Integration

The `run_hydra.py` entry point demonstrates how to use **Hydra for configuration** and **ZenML for orchestration**:

**Separation of concerns**:
- **Hydra** decides WHAT: search space ranges, model architecture, data paths
- **ZenML** decides WHERE/WHEN: orchestration, scheduling, caching, artifact tracking

**Example workflow**:

```bash
# Define search space in conf/config.yaml
python run_hydra.py

# Override from CLI for quick experiments
python run_hydra.py search_space.learning_rate.low=1e-5 sweep.n_trials=20

# Hydra composes config from multiple sources
python run_hydra.py -cn experiment_config
```

The resolved config is:
1. Passed to `suggest_trials` step via the `search_space` parameter (overrides hardcoded defaults)
2. Visible in dashboard metadata

**How the wiring works**: The `suggest_trials` step accepts an optional `search_space: Dict[str, Any]` parameter. When `run_hydra.py` calls the pipeline, it passes `search_space=config["search_space"]`, which contains the Hydra-resolved ranges. The step uses these if provided, otherwise falls back to hardcoded defaults. This means you can:
- Run with defaults: `python run.py` (uses hardcoded ranges in `suggest.py`)
- Run with Hydra: `python run_hydra.py` (uses ranges from `conf/config.yaml`)
- Override via CLI: `python run_hydra.py search_space.learning_rate.high=0.5`

This pattern is useful for teams that use Hydra heavily and need it to work seamlessly with ZenML.

## Project Structure

```
examples/optuna_sweep/
+-- README.md                    # This file
+-- requirements.txt             # Dependencies (optuna, torch, hydra)
+-- run.py                       # Basic entry point (simple/adaptive modes)
+-- run_hydra.py                 # Hydra integration entry point
+-- conf/
|   +-- config.yaml              # Hydra configuration
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

## Success Criteria

- **Run end-to-end locally**: `python run.py` completes without errors
- **Dashboard shows parallel DAG**: N training steps fan out from suggest
- **Results table prints**: Report step shows all trials with metrics
- **Adaptive mode works**: Multiple rounds visible in DAG, later rounds informed by earlier results
- **Metadata is queryable**: Each trial artifact has val_loss, learning_rate, batch_size, hidden_dim
- **Hydra integration works**: `python run_hydra.py` runs with config composition

## Troubleshooting

### `CategoricalDistribution does not support dynamic value space`

This can happen if you modified the search space choices between runs. Since studies are in-memory and seeded from artifact history, changing the choices while previous artifacts still exist can cause conflicts.

**Fix**: Start a new study by changing `STUDY_NAME` in `run.py` or passing a different name via Hydra:
```bash
python run_hydra.py sweep.study_name=my_new_sweep
```

## Further Reading

- **ZenML Dynamic Pipelines**: [docs.zenml.io/how-to/dynamic-pipelines](https://docs.zenml.io/how-to/dynamic-pipelines)
- **Hyperparameter Tuning Guide**: [docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning](https://docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning)
- **Resource Pools**: [docs.zenml.io/how-to/resource-pools](https://docs.zenml.io/how-to/resource-pools)
- **Optuna Documentation**: [optuna.readthedocs.io](https://optuna.readthedocs.io)
- **Hydra Documentation**: [hydra.cc](https://hydra.cc)

## Need Help?

- **ZenML Slack**: [zenml.io/slack](https://zenml.io/slack)
- **GitHub Issues**: [github.com/zenml-io/zenml/issues](https://github.com/zenml-io/zenml/issues)
- **Docs**: [docs.zenml.io](https://docs.zenml.io)
