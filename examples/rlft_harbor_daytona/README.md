# Harbor Eval Campaign Pipeline

A ZenML dynamic pipeline that orchestrates [Harbor](https://github.com/harbor-ai/harbor) agent evaluations across a configurable matrix of agents and models. Harbor is the standard for containerized agent evaluation; ZenML adds the "outer loop" — reproducible campaigns with fan-out, artifact lineage, and reporting.

## Pipeline DAG

```
build_matrix
     |
+---------+---------+
|         |         |
run_0   run_1    run_N      ← one per (agent, model) combo
|         |         |
parse_0 parse_1  parse_N
|         |         |
+---------+---------+
          |
    build_report
```

The number of parallel run/parse pairs is determined at runtime from the config file's `agents × models` matrix.

## Quick Start

### Prerequisites

- Python 3.9+
- Docker (for Harbor task containers)
- ZenML installed: `pip install "zenml>=0.93"`
- Harbor installed: `pip install harbor`

### Install

```bash
cd rlft_example
pip install -r requirements.txt
```

### Run with Oracle Agent (no API keys needed)

The oracle agent runs the reference solution for each task — useful for verifying that the pipeline infrastructure works:

```bash
python run.py --config configs/dev.yaml
```

### Run with Custom Config

```bash
python run.py --config configs/prod.yaml
```

## Configuration

Campaign configs live in `configs/`. Each config defines:

```yaml
campaign:
  name: dev-oracle-local
  dataset_path: datasets/mini_harbor    # Path to task dataset
  agents:
    - oracle                            # Harbor agent names
  models: []                            # LLM models (empty = no model needed)
  env_provider: null                    # null for local Docker, 'daytona' for remote
  n_concurrent: null                    # Concurrent tasks within a job
  extra_args: []                        # Extra CLI args for `harbor run`
```

**Matrix logic**: Oracle agents always get `model=None`. Non-oracle agents get one run per model in the list (cartesian product).

## Bundled Mini Dataset

Three minimal tasks under `datasets/mini_harbor/` for fast testing:

| Task | What the Agent Must Do | Verification |
|------|----------------------|-------------|
| `create-file` | Create `output.txt` with "hello world" | File exists, content matches |
| `fix-syntax-error` | Fix missing `)` in `app.py` | `python app.py` prints "success" |
| `add-function` | Add `add(a, b)` to `math_utils.py` | Import works, assertions pass |

## Project Structure

| Path | Purpose |
|------|---------|
| `run.py` | CLI entry point |
| `pipelines/harbor_eval_campaign.py` | Dynamic pipeline with fan-out loop |
| `steps/build_matrix.py` | Config → list of HarborRunSpec |
| `steps/run_harbor_job.py` | HarborRunSpec → job directory (via subprocess) |
| `steps/parse_harbor_job.py` | Job directory → JobSummary |
| `steps/build_report.py` | List of summaries → CampaignReport + HTML |
| `models/harbor_models.py` | Pydantic data types |
| `utils/harbor_cli.py` | Harbor CLI command builder |
| `configs/` | Campaign YAML configs |
| `datasets/mini_harbor/` | Bundled test tasks |
| `data/` | HTML report template and CSS |

## Running on Kubernetes

For K8s orchestrators, Harbor tasks need a Docker-capable environment. Options:

1. **Daytona** (recommended): Set `env_provider: daytona` in your config. Harbor uses Daytona's remote environment — no Docker-in-Docker needed.

2. **Docker socket mount** (future work): Mount the host Docker socket into the step container.

## Key ZenML Patterns

This pipeline demonstrates several ZenML dynamic pipeline features:

- **`@pipeline(dynamic=True)`** — DAG shape determined at runtime
- **`.load()`** — Materializes artifact value for control flow (getting list length)
- **`.chunk(index=idx)`** — Creates DAG edge without materializing (parallel fan-out)
- **`PathMaterializer`** — Built-in directory archiving (Harbor job dirs → tar.gz artifacts)
- **`HTMLString`** — Custom visualization type rendered in the ZenML dashboard
