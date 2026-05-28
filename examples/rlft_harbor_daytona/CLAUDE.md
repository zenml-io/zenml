# CLAUDE.md

This file provides guidance to Claude Code when working with code in this directory.

## What This Is

A complete, runnable ZenML dynamic pipeline that orchestrates Harbor agent evaluations across an agent × model matrix. It lives in the ZenML monorepo at `examples/rlft_harbor_daytona/`. See the root `CLAUDE.md` for ZenML-wide conventions.

This is the eval-campaign foundation of a larger RLFT (Reinforcement Learning from Feedback/Testing) story. Extensions like trace export, training, and re-eval are additive steps on top of this pipeline, not part of the current code.

## Commands

```bash
# Install dependencies (run from this directory)
pip install -r requirements.txt

# Run with oracle agent (no API keys needed)
python run.py --config configs/dev.yaml

# Run with production config
python run.py --config configs/prod.yaml

# Test a single mini task directly with Harbor
harbor run -p datasets/mini_harbor/create-file -a oracle
```

`configs/` holds four campaign configs: `dev.yaml` (oracle, local), `prod.yaml` (multi-agent × multi-model via Daytona), `stress.yaml` (larger local matrix), `k8s_stress.yaml` (sized for Kubernetes + Daytona). `datasets/mini_harbor/` contains seven deterministic tasks, each with a reference solution the oracle agent runs.

## Architecture

### Pipeline DAG (determined at runtime)

```
build_matrix → [run_harbor_job_N → parse_harbor_job_N] → build_report
```

Fan-out count equals `len(agents) * len(models)` from the YAML config (oracle agents skip the model dimension).

### Module Layout

| Module | Role |
|--------|------|
| `run.py` | CLI entry point with argparse |
| `pipelines/harbor_eval_campaign.py` | `@pipeline(dynamic=True)` with fan-out loop |
| `steps/build_matrix.py` | YAML config → `List[HarborRunSpec]` |
| `steps/run_harbor_job.py` | Subprocess `harbor run` → `Path` (job dir) |
| `steps/parse_harbor_job.py` | Job dir → `JobSummary` dict via `model_dump()` (defensive parsing; dict because dynamic list-collection uses the JSON materializer) |
| `steps/build_report.py` | Summaries → `CampaignReport` + `HTMLString` |
| `models/harbor_models.py` | Pydantic data types: HarborRunSpec, TrialResult, JobSummary, CampaignReport |
| `utils/harbor_cli.py` | `build_harbor_command()`, `find_job_dir()` |

### Key Patterns

- **Dynamic fan-out**: `.load()` materializes for control flow, `.chunk(index=idx)` creates DAG edges
- **PathMaterializer**: Built-in, archives directories as `.tar.gz` — no custom materializer
- **Pydantic BaseModel**: Built-in materializer, validation, JSON serialization
- **Defensive parsing**: `parse_harbor_job` never crashes on missing data
- **Report assets**: External CSS + HTML template loaded via `_load_text_asset()` with path fallbacks

### Config Format

```yaml
campaign:
  name: dev-oracle-local
  dataset_path: datasets/mini_harbor
  agents: [oracle]
  models: []
  env_provider: null
  n_concurrent: null
```

## Current Scope

- Eval campaign only — improvement loop, training, and verifiers are additive extensions, not yet implemented
- Dynamic pipelines run on the local, local-docker, Kubernetes, Vertex, SageMaker, and AzureML orchestrators (ZenML 0.93+). Harbor still needs a Docker-capable environment per step: local Docker locally, or `env_provider: daytona` when steps run on K8s without a usable Docker daemon
- Oracle agent for testing (no API keys); real agents need the relevant LLM keys (use `run.py --forward-env` to forward them to remote pods)
