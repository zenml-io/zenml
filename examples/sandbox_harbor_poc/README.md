# Harbor Eval Campaigns on the ZenML Sandbox

Run [Harbor](https://harborframework.org) agent evaluations across an agent x model matrix as a single ZenML pipeline, with every trial executing on whatever Sandbox component is on your active stack.

**ZenML version**: 0.95+ (Python 3.10+)

## 🎯 What You'll Learn

- Fan out a Harbor evaluation across an `agent x model` matrix with a `dynamic=True` ZenML pipeline
- Run Harbor programmatically (no `harbor run` CLI, no Docker/Daytona env provider) through the `ZenMLSandboxEnvironment` bridge
- Capture every trial's reward, logs, and the full job tree as versioned ZenML artifacts
- Produce a ranked leaderboard `CampaignReport` plus a self-contained HTML report visualization
- Swap the execution substrate by changing the Sandbox flavor on your stack — the same campaign runs anywhere without a pipeline code change

## What you get over plain `harbor run`

A single `harbor run` evaluates one agent against one dataset and leaves the results on disk. This example adds three layers on top:

- **Matrix campaigns.** One config drives N jobs — every `(agent, model)` combination fans out into its own `run_harbor_job` + `parse_harbor_job` pair, then merges into one report.
- **Leaderboard + HTML report.** `build_report` ranks every combo by pass rate, surfaces the tasks that fail across the board, and renders an `agent x task` matrix as an HTML artifact you can open straight from the dashboard.
- **Versioned, queryable artifacts.** Each job's full on-disk tree (agent transcripts, verifier output, rewards) is archived as a ZenML artifact with full lineage — re-openable, comparable across runs, never lost on disk.

## 🏃 Quickstart

Oracle agent on the mini_harbor dataset — no API keys required:

```bash
pip install -r requirements.txt
# Install sandbox and stack requirements
zenml integration install modal s3
# Register a stack with a Sandbox component (see Prerequisites), then:
python run.py --config configs/dev.yaml
```

## 📋 Prerequisites

- Python 3.10 or higher
- A ZenML stack whose active components include a **Sandbox** component (e.g. a Modal sandbox flavor). The bridge resolves it via `Client().active_stack.sandbox`.
- [Harbor](https://harborframework.org) (`harbor>=0.8.0`, installed via `requirements.txt`)
- Modal credentials if using the Modal flavor: `modal token new` (writes `~/.modal.toml`) or `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`
- For non-oracle agents only: `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` exported locally, forwarded with `--forward-env`. The `oracle` agent in `configs/dev.yaml` needs none.

## 🏗️ What's Inside

```
📁 sandbox_harbor_poc/
├── zenml_sandbox_env.py         - ZenMLSandboxEnvironment: the Harbor BaseEnvironment → Sandbox bridge
├── run.py                       - CLI entry point (--config, --forward-env)
├── pipelines/
│   └── harbor_eval_campaign.py  - @pipeline(dynamic=True) matrix fan-out
├── steps/
│   ├── build_matrix.py          - Read YAML config → List[HarborRunSpec]
│   ├── run_harbor_job.py        - Run one Harbor job via the Sandbox bridge → job_dir
│   ├── parse_harbor_job.py      - Parse job tree → JobSummary dict
│   └── build_report.py          - Aggregate → CampaignReport + HTML report
├── models/
│   └── harbor_models.py         - Typed step-to-step contract (4 Pydantic models)
├── configs/
│   ├── dev.yaml                 - oracle on mini_harbor (no keys)
│   └── prod.yaml                - oracle + terminus-2 x {gpt-4o, claude-sonnet-4}
├── datasets/mini_harbor/        - 7 hermetic Harbor tasks
├── data/                        - HTML report template + CSS
└── requirements.txt
```

The typed contract in `models/harbor_models.py` is the spine: `build_matrix` emits `HarborRunSpec`s, `run_harbor_job` turns each into a job tree, `parse_harbor_job` extracts a `JobSummary`, and `build_report` merges them into a `CampaignReport`.

## 🔑 Key Concepts

### Dynamic fan-out over the matrix

The pipeline is `dynamic=True`, so the DAG shape is decided at runtime from the config's matrix. `build_matrix` returns a list of specs, and `.map` fans out one branch per item — `run_harbor_job` runs per spec, and its results are zipped back against the same matrix so `parse_harbor_job` sees each job tree next to the spec that produced it:

```python
@pipeline(dynamic=True, enable_cache=False, settings={"docker": docker_settings})
def harbor_eval_campaign(config_path: str = "configs/dev.yaml") -> Tuple[
    Annotated[CampaignReport, "campaign_report"],
    Annotated[HTMLString, "report"],
]:
    matrix = build_matrix(config_path=config_path)
    job_dirs = run_harbor_job.map(spec=matrix)
    summaries = parse_harbor_job.map(job_dir=job_dirs, spec=matrix)
    return build_report(job_summaries=summaries)
```

The resulting DAG, for an N-row matrix:

```
            build_matrix
                 |
     +-----------+-----------+
     |           |           |
   run_0       run_1   ...  run_N      <- one per (agent, model) combo
     |           |           |
   parse_0     parse_1 ...  parse_N
     |           |           |
     +-----------+-----------+
                 |
            build_report
```

### Harbor on the Sandbox bridge

`run_harbor_job` never shells out. It builds a single-task `JobConfig` whose environment is the bridge, so the trial runs inside the active stack's Sandbox:

```python
config = JobConfig(
    jobs_dir=jobs_dir,
    n_concurrent_trials=1,
    quiet=True,
    tasks=[TaskConfig(path=str(task_path))],   # one task per step
    agents=[_build_agent_config(spec)],
    environment=EnvironmentConfig(
        import_path="zenml_sandbox_env:ZenMLSandboxEnvironment"
    ),
    verifier=VerifierConfig(),
)
job = await Job.create(config)
await job.run()
```

### Named artifacts with `Annotated`

Every step output is named so lineage is readable in the dashboard — `job_dir`, `job_summary`, `campaign_report`, and `report`:

```python
@step(enable_cache=False)
def run_harbor_job(spec: HarborRunSpec) -> Annotated[Path, "job_dir"]:
    ...
```

The `job_dir` output is a `Path`; ZenML's built-in `PathMaterializer` archives the entire Harbor job tree as a versioned `.tar.gz` artifact, preserving agent transcripts, verifier logs, and rewards.

## 🚀 Run the Example

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   zenml integration install modal
   ```

2. **Register a stack with a Sandbox component** (Modal shown; substitute your flavor)
   ```bash
   zenml sandbox register modal-sb --flavor=modal
   zenml stack register harbor-stack -o default -a default --sandbox modal-sb --set
   ```

3. **Run the oracle campaign** (no API keys needed)
   ```bash
   python run.py --config configs/dev.yaml
   ```
   The run prints a dashboard URL on start. `configs/dev.yaml` evaluates the `oracle` agent across all 7 mini_harbor tasks.

4. **Run the full matrix** (forwards your LLM keys into the Sandbox)
   ```bash
   export OPENAI_API_KEY=...        # and/or ANTHROPIC_API_KEY
   python run.py --config configs/prod.yaml --forward-env
   ```
   `configs/prod.yaml` fans out `oracle` + `terminus-2 x {gpt-4o, claude-sonnet-4}`.

5. **Inspect the report artifacts**
   ```python
   from zenml.client import Client

   run = Client().get_pipeline_run("<run-id-from-stdout>")
   report = run.steps["build_report"].outputs["campaign_report"][0].load()
   print(report.ranked)          # leaderboard rows, best pass_rate first
   print(report.failing_tasks)   # tasks no agent solved
   ```
   The HTML `report` artifact renders the `agent x task` matrix and leaderboard — open it directly from the artifact view in the dashboard.

## 🧪 Customization Ideas

- **Add agents or models**: edit the `agents` / `models` lists in `configs/prod.yaml` — the DAG expands automatically.
- **Bring your own dataset**: point `dataset_path` at any directory of Harbor tasks (one `*/task.toml` per task); `run_harbor_job` enumerates them.
- **Raise trial concurrency**: set `n_concurrent` in the config to parallelize tasks within a single job.
- **Swap the substrate**: register a different Sandbox flavor and `--set` it as active — no code change to run the same campaign elsewhere.
- **Customize the report**: edit `data/report_template.html` / `data/report.css` to reshape the leaderboard or matrix table.

## Limitations

A few things to know before you extend the example:

- **Resource translation.** Harbor task resource hints (`cpus` / `memory_mb` / `gpus`) do not flow into the active Sandbox flavor's `ResourceSettings` yet, so trials run with the flavor's defaults.
- **`env_provider` is ignored.** The field is accepted in configs and on `HarborRunSpec` for compatibility, but the Sandbox bridge owns execution — there is no Harbor env provider on this path, so the value has no effect.

## 📚 Learn More

- [ZenML Steps & Pipelines](https://docs.zenml.io/concepts/steps_and_pipelines)
- [Dynamic Pipelines](https://docs.zenml.io/concepts/steps_and_pipelines/dynamic_pipelines)
- [Artifact Management with Annotated Types](https://docs.zenml.io/concepts/artifacts)
- [Custom Visualizations (HTML artifacts)](https://docs.zenml.io/concepts/artifacts/visualizations)
- [Harbor](https://harborframework.org)
