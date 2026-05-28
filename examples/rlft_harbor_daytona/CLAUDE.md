# CLAUDE.md

This file provides guidance to Claude Code when working with code in this directory.

## What This Is

Phase 1 of the RLFT (Reinforcement Learning from Feedback/Testing) example: a ZenML dynamic pipeline that orchestrates Harbor agent evaluations. This lives in the ZenML monorepo at `rlft_example/`. See the root `CLAUDE.md` for ZenML-wide conventions.

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
| `steps/parse_harbor_job.py` | Job dir → `JobSummary` (defensive parsing) |
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

## Phase 1 Scope

- Eval campaign only (no improvement loop, no training, no verifiers)
- Local + LocalDocker orchestrators (K8s needs Daytona env provider)
- Oracle agent for testing (no API keys)
