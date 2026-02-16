# Hyperparameter Sweeps with Optuna + ZenML Dynamic Pipelines

A production-ready example demonstrating intelligent hyperparameter optimization using **Optuna's ask/tell API** combined with **ZenML dynamic pipelines** for parallel trial execution. Train multiple models in parallel, leverage GPU resource pools, and track everything in the ZenML dashboard.

## 🎯 What This Demonstrates

- **Optuna integration**: Use Optuna's ask/tell API for intelligent hyperparameter sampling
- **Dynamic pipelines**: Fan out trials in parallel using `step.map()`
- **Resource management**: Efficient parallel execution with configurable resource pools
- **Metadata tracking**: Every trial's metrics are logged and queryable via the ZenML dashboard and MCP server
- **Two optimization patterns**: Simple parallel sweep vs. adaptive multi-round optimization
- **Hydra integration**: Optional config composition for complex search spaces

## 🏗️ Architecture

```
Optuna Study (Persistent)
    │
    ├─→ Ask API: Generate trial configs
    │       │
    │       ├─→ ZenML Pipeline: Orchestrate parallel training
    │       │       │
    │       │       ├── train_trial_0 ──┐
    │       │       ├── train_trial_1   ├── Parallel execution
    │       │       ├── train_trial_2   │   (managed by orchestrator)
    │       │       └── train_trial_N ──┘
    │       │               │
    │       └───────────────┴─→ Collect results
    │
    └─→ Tell API: Report trial outcomes, inform next round
```

**Key insight**: Optuna decides *what* to try next (smart sampling). ZenML decides *where* and *when* to run it (orchestration, parallelism, caching).

## 🚀 Quick Start

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

This runs 5 trials in parallel, training an MLPClassifier on FashionMNIST with different hyperparameters (learning rate, L2 regularization, hidden layer architecture). Training runs for up to 100 iterations per trial.

### Run the Adaptive Sweep

Multiple rounds where each round learns from the previous:

```bash
python run.py adaptive
```

This runs 3 rounds of 3 trials each (9 trials total), with 100 training iterations per trial. Optuna's sampler uses early results to suggest better hyperparameters in later rounds.

### Run with Hydra Configuration

Manage complex search spaces and configuration with Hydra:

```bash
# Uncomment Hydra dependencies in requirements.txt first
pip install hydra-core omegaconf

# Simple mode (default from conf/config.yaml)
python run_hydra.py

# Adaptive mode
python run_hydra.py sweep.mode=adaptive

# Override from CLI
python run_hydra.py sweep.n_trials=10                            # More trials (simple mode)
python run_hydra.py sweep.mode=adaptive sweep.n_rounds=5         # Adaptive with 5 rounds
python run_hydra.py search_space.learning_rate_init.high=0.5     # Override search space
python run_hydra.py sweep.max_iter=200 sweep.n_trials=20         # Multiple overrides
```

## 📊 What You'll See in the Dashboard

### Simple Sweep DAG

```
suggest_trials (generates 5 configs)
     │
     ├── train_trial_0 ──┐
     ├── train_trial_1   │
     ├── train_trial_2   ├── All run in parallel
     ├── train_trial_3   │   (managed by orchestrator)
     ├── train_trial_4 ──┘
             │
        report_results (tells Optuna, prints summary)
             │
        retrain_best_model (saves production model)
```

**Key insight**: Trial models are discarded (only metrics saved). After finding the best hyperparameters, the pipeline retrains with those params and saves only that production-ready model.

### Adaptive Sweep DAG

```
Round 1:
  suggest_trials_round_0
       ├── train_trial_0, 1, 2 (parallel)
       └── report_results_round_0

Round 2:
  suggest_trials_round_1 (learns from round 1)
       ├── train_trial_3, 4, 5 (parallel)
       └── report_results_round_1

Round 3:
  suggest_trials_round_2 (learns from rounds 1 & 2)
       ├── train_trial_6, 7, 8 (parallel)
       └── report_results_round_2
            │
       retrain_best_model (saves production model)
```

### Metadata & Artifacts

Each trial artifact has rich metadata attached:

```python
{
  "trial_number": 3,
  "val_loss": 0.1548,
  "val_accuracy": 84.52,
  "learning_rate_init": 0.003421,
  "alpha": 0.000285,
  "hidden_layer_sizes": (128, 64),
  "training_losses": [0.612, 0.458, 0.423],
}
```

This makes trials **queryable**:
- Via dashboard: filter/sort by val_loss, learning_rate_init, etc.
- Via MCP server: "show me all trials with val_loss < 0.4"
- Via ZenML client: `client.list_artifact_versions()` with metadata filters

## 🔧 How It Works

### 1. Suggest Trials (`steps/suggest.py`)

Optuna's **ask API** generates trial configurations:

```python
study = optuna.create_study(...)
trials = []
for _ in range(n_trials):
    trial = study.ask()  # Get next trial to evaluate
    config = {
        "trial_number": trial.number,
        "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-1, log=True),
        "alpha": trial.suggest_float("alpha", 1e-5, 1e-1, log=True),
        "hidden_layer_sizes": trial.suggest_categorical("hidden_layer_sizes", [(64,), (128,), (64, 32), (128, 64)]),
    }
    trials.append(config)
```

Returns a list of configs, one per trial.

### 2. Train in Parallel (`steps/train.py`)

Each trial trains independently:

```python
@step
def train_trial(trial_config: dict) -> dict:
    model = MLPClassifier(
        hidden_layer_sizes=trial_config["hidden_layer_sizes"],
        learning_rate_init=trial_config["learning_rate_init"],
        alpha=trial_config["alpha"]
    )

    # Train and evaluate...
    model.fit(X_train, y_train)
    val_score = model.score(X_val, y_val)
    val_loss = 1.0 - val_score

    # Log metadata for dashboard/MCP queries
    log_metadata({
        "trial_number": trial_config["trial_number"],
        "val_loss": val_loss,
        "learning_rate_init": trial_config["learning_rate_init"],
        ...
    })

    return {"trial_number": ..., "val_loss": val_loss, ...}
```

**Note**: MLPClassifier from scikit-learn doesn't use GPUs, but the resource management principles remain the same for other ML frameworks.

### 3. Report Results (`steps/report.py`)

Optuna's **tell API** records trial outcomes:

```python
study = optuna.load_study(...)
for result in results:
    study.tell(result["trial_number"], result["val_loss"])

best_trial = study.best_trial
print(f"Best val_loss: {best_trial.value}")
print(f"Best params: {best_trial.params}")
```

Prints a summary table and returns the best trial found.

### 4. Save Best Model (`steps/save_best.py`)

After finding the best hyperparameters, retrain with more iterations:

```python
@step
def retrain_best_model(sweep_summary: dict, max_iter: int = 200):
    best_params = sweep_summary["best_params"]

    # Retrain with best hyperparameters + more iterations
    model = MLPClassifier(
        hidden_layer_sizes=best_params["hidden_layer_sizes"],
        learning_rate_init=best_params["learning_rate_init"],
        alpha=best_params["alpha"],
        max_iter=200,  # More than trials (100)
        early_stopping=True,  # Enable for production
    )
    model.fit(X_train, y_train)

    # Log metadata on the model artifact
    log_metadata(metadata={...}, infer_artifact=True)
    log_model_metadata(metadata={...})  # For Model Control Plane

    return model  # Saved as ZenML artifact
```

**Why this approach?**
- ✅ **No storage waste**: Trial models discarded (only metrics saved)
- ✅ **Production-ready**: Best model gets extra training (200 vs 100 iterations)
- ✅ **Queryable**: Model metadata logged for dashboard/MCP queries
- ✅ **Reproducible**: Hyperparameters logged, can retrain anytime

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

## 🎓 Two Optimization Patterns

### Pattern 1: Simple Parallel Sweep

**When to use**: Small-scale sweeps where you want maximum parallelism.

```python
sweep_pipeline(n_trials=10)
```

- All 10 trials suggested upfront
- All 10 train in parallel (or queued by GPU availability)
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

## 🌐 Remote Execution & Production Deployment

### SQLite Limitation

The default `sqlite:///optuna_study.db` works great for local development but **won't work in distributed/containerized environments** (each container sees its own filesystem).

**For production/cloud execution**, replace the storage with a proper database:

```python
# PostgreSQL
storage_url = "postgresql://user:pass@host:5432/optuna"

# MySQL
storage_url = "mysql://user:pass@host:3306/optuna"
```

Then all containers share the same Optuna study state.

### Resource Pools

When you configure resource pools in ZenML, the pipeline automatically manages parallel execution across available resources. No code changes needed. The same `train_trial` step works locally and in production environments.

## 🤝 Hydra + ZenML Integration

The `run_hydra.py` entry point demonstrates how to use **Hydra for configuration** and **ZenML for orchestration**:

**Separation of concerns**:
- **Hydra** decides WHAT: search space ranges, model architecture, data paths
- **ZenML** decides WHERE/WHEN: orchestration, GPU scheduling, caching, artifact tracking

**Example workflow**:

```bash
# Define search space in conf/config.yaml
python run_hydra.py

# Override from CLI for quick experiments
python run_hydra.py search_space.lr.low=1e-5 sweep.n_trials=20

# Hydra composes config from multiple sources
python run_hydra.py -cn experiment_config
```

The resolved config is:
1. Logged as a ZenML artifact (traceability)
2. Passed to `suggest_trials` step via the `search_space` parameter (overrides hardcoded defaults)
3. Visible in dashboard metadata

**How the wiring works**: The `suggest_trials` step accepts an optional `search_space: Dict[str, Any]` parameter. When `run_hydra.py` calls the pipeline, it passes `search_space=config["search_space"]`, which contains the Hydra-resolved ranges. The step uses these if provided, otherwise falls back to hardcoded defaults. This means you can:
- Run with defaults: `python run.py` (uses hardcoded ranges in `suggest.py`)
- Run with Hydra: `python run_hydra.py` (uses ranges from `conf/config.yaml`)
- Override via CLI: `python run_hydra.py search_space.learning_rate_init.high=0.5`

This is critical for **Robin Radar's use case** — their team uses Hydra heavily and needs to see it working seamlessly with ZenML.

## 📁 Project Structure

```
examples/optuna_sweep/
├── README.md                    # This file
├── requirements.txt             # Dependencies (optuna, torch, optional hydra)
├── run.py                       # Basic entry point (simple/adaptive modes)
├── run_hydra.py                 # Hydra integration entry point
├── conf/
│   └── config.yaml              # Hydra configuration
├── pipelines/
│   ├── __init__.py
│   └── sweep.py                 # sweep_pipeline + adaptive_sweep_pipeline
└── steps/
    ├── __init__.py
    ├── suggest.py               # Optuna ask API
    ├── train.py                 # Single trial training
    └── report.py                # Optuna tell API + results summary
```

## 🎯 Success Criteria

✅ **Run end-to-end locally**: `python run.py` completes without errors
✅ **Dashboard shows parallel DAG**: N training steps fan out from suggest
✅ **Results table prints**: Report step shows all trials with metrics
✅ **Study persistence works**: Running twice appends to same Optuna study
✅ **Adaptive mode works**: Multiple rounds visible in DAG
✅ **Metadata is queryable**: Each trial artifact has val_loss, lr, dropout, etc.
✅ **Hydra integration works**: `python run_hydra.py` runs with config composition

## 🐛 Troubleshooting

### Optuna Study Already Exists / "Dynamic Value Space" Error

If you see `CategoricalDistribution does not support dynamic value space` or want to start fresh:

```bash
# Delete the old study
rm optuna_study.db

# Run again
python run.py
```

**Why this happens**: Optuna enforces consistent categorical choices across trials. If you modified the search space or updated the code, the old study is incompatible.

**Alternative - use a new study name**:
```bash
# With Hydra
python run_hydra.py sweep.study_name=my_new_sweep

# Or modify STUDY_NAME in run.py
```

## 🔗 Further Reading

- **ZenML Dynamic Pipelines**: [docs.zenml.io/how-to/dynamic-pipelines](https://docs.zenml.io/how-to/dynamic-pipelines)
- **Hyperparameter Tuning Guide**: [docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning](https://docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning)
- **Resource Pools**: [docs.zenml.io/how-to/resource-pools](https://docs.zenml.io/how-to/resource-pools)
- **Optuna Documentation**: [optuna.readthedocs.io](https://optuna.readthedocs.io)
- **Hydra Documentation**: [hydra.cc](https://hydra.cc)

## 💬 Need Help?

- **ZenML Slack**: [zenml.io/slack](https://zenml.io/slack)
- **GitHub Issues**: [github.com/zenml-io/zenml/issues](https://github.com/zenml-io/zenml/issues)
- **Docs**: [docs.zenml.io](https://docs.zenml.io)
