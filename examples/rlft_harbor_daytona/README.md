# Harbor Eval Campaigns on ZenML

You already run agent evaluations with [Harbor](https://github.com/harbor-ai/harbor).
Harbor is excellent at what it does: it takes a containerized task — an
instruction, a Dockerfile, a verifier — drops an agent into the sandbox, and
tells you whether the agent passed. This example does not try to replace any of
that. Harbor stays the evaluator.

What this example adds is the **layer around** Harbor: the part that turns "I ran
an eval once and looked at the result" into "I run evals repeatedly, across a
whole matrix of agents and models, and every run is versioned, comparable, and
reproducible six months later."

That outer layer is a ZenML *dynamic pipeline*. It calls `harbor run` for you,
captures the full output of every job as a versioned artifact, and rolls
everything up into a leaderboard you can open in the ZenML dashboard.

## The problem this actually solves

Running one Harbor eval is easy. The pain starts when evals become part of how
you work:

- You want to compare three agents across two models — that's six runs, and you
  want them side by side, not in six terminal scrollbacks.
- You ran a campaign last Tuesday and a different one today. Which agent
  regressed? You need last Tuesday's raw job output still sitting somewhere you
  can pull it from.
- Someone asks "how did we get this number?" and you need the exact job
  directory, the exact config, and the exact model that produced it — not a
  vague memory.

Harbor produces all the right raw material (job directories, per-trial rewards,
logs). What it does not give you on its own is the **operational memory** around
many runs over time: lineage, versioning, and a stable place to stand when you
compare run N against run N-1. That gap is what ZenML fills here.

Concretely, after a campaign runs:

- Every `harbor run` job directory is tarred and stored as a **versioned
  artifact** in the ZenML artifact store. The output of campaign run #47 is still
  there, byte for byte, when you need it.
- Each job carries **logged metadata** — the agent, the model, the pass rate,
  Harbor's exit code — queryable later without re-reading log files.
- The whole campaign collapses into one **`CampaignReport` artifact** plus an
  **HTML leaderboard** rendered in the dashboard, so "which combination won" is a
  glance, not an investigation.

## Pipeline DAG

The shape is decided at runtime from your config's `agents × models` matrix:

```
build_matrix
     |
+---------+---------+
|         |         |
run_0   run_1    run_N      <- one branch per (agent, model) combo
|         |         |
parse_0 parse_1  parse_N
|         |         |
+---------+---------+
          |
    build_report
```

You don't write the fan-out by hand. `build_matrix` returns a list, and the
pipeline loops over its length at runtime to spawn one `run_harbor_job →
parse_harbor_job` branch per entry. Three agent/model combinations gives three
branches; twelve gives twelve. This is the genuine use of a dynamic pipeline —
the DAG doesn't exist until ZenML reads your config.

## How it works, step by step

1. **`build_matrix`** reads a YAML config and expands it into a list of
   `HarborRunSpec` objects, one per `(agent, model)` pair. Oracle agents need no
   model, so they skip that dimension; every other agent gets the cartesian
   product of itself against each model in the list.

2. **`run_harbor_job`** runs `harbor run -a <agent> -m <model> -p <dataset>` in an
   isolated temp directory and returns the path to Harbor's job-output folder.
   ZenML's built-in `PathMaterializer` archives that whole folder into a `.tar.gz`
   artifact — this is the step that gives you reproducibility.

3. **`parse_harbor_job`** walks each trial subdirectory, reads `result.json`
   (reward, task name, timing, any exception), and produces a `JobSummary`. It is
   written defensively: missing or malformed files degrade to "no reward
   recorded" rather than crashing the campaign.

4. **`build_report`** aggregates every `JobSummary` into a `CampaignReport`: a
   leaderboard ranked by pass rate, an agent × task pass/fail matrix, and the list
   of tasks that failed for *every* combination (your hardest tasks). It also
   renders an HTML version for the dashboard.

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (Harbor builds and runs each task in a container)
- ZenML: `pip install "zenml[local,server]>=0.93"`
- Harbor: `pip install "harbor>=0.1.0"`

The full dependency set is in `requirements.txt`.

### Install

```bash
cd rlft_harbor_daytona
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
```

### Run with the oracle agent (no API keys needed)

The `oracle` agent runs each task's reference solution instead of calling an LLM.
It's the fastest way to confirm the whole pipeline works end to end — it should
pass every task:

```bash
python run.py --config configs/dev.yaml
```

Open the run in the ZenML dashboard and you'll see the DAG, the per-job
artifacts, and the rendered HTML leaderboard.

### Run a real agent × model matrix

```bash
python run.py --config configs/prod.yaml
```

This fans out `oracle` plus `terminus-2` across `gpt-4o` and
`claude-sonnet-4-20250514`. You'll need the relevant API keys set in your
environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

## Configuration

Campaign configs live in `configs/`. Every field:

```yaml
campaign:
  name: dev-oracle-local          # campaign label (shows up in logs/reports)
  dataset_path: datasets/mini_harbor   # local Harbor dataset directory
  dataset_ref: null               # OR a registry dataset ref (e.g. a hub dataset)
  agents:
    - oracle                      # Harbor agent names
  models: []                      # LLM models; empty = no model dimension
  env_provider: null              # null = local Docker; 'daytona' = remote sandbox
  n_concurrent: null              # trials Harbor runs in parallel *within* a job
  extra_args: []                  # extra args passed straight to `harbor run`
```

**Matrix rule:** the `oracle` agent (and any run with an empty `models` list)
gets `model=None`. Every other agent gets one run per model — the cartesian
product.

The repo ships four configs so you can see the range:

| Config | What it shows |
|--------|---------------|
| `dev.yaml` | Smallest possible run — oracle only, local Docker. Start here. |
| `prod.yaml` | Multi-agent × multi-model, run remotely via Daytona. |
| `stress.yaml` | A larger local matrix (oracle + aider × two models). |
| `k8s_stress.yaml` | A matrix sized for a Kubernetes orchestrator + Daytona. |

## The bundled mini dataset

Seven tiny, deterministic Harbor tasks live under `datasets/mini_harbor/`. They
run in seconds, need no network, and each has a clean pass/fail verifier plus a
reference solution (which is what `oracle` executes):

| Task | What the agent must do |
|------|------------------------|
| `create-file` | Write `output.txt` containing exactly `hello world` |
| `fix-syntax-error` | Repair a missing parenthesis so `app.py` prints `success` |
| `add-function` | Implement `add(a, b)` in an empty `math_utils.py` |
| `count-lines` | Count lines in `input.txt`, write the number to `result.txt` |
| `write-json` | Produce a `data.json` with three exact key/value pairs |
| `merge-files` | Concatenate `part1.txt` + `part2.txt` into `merged.txt` |
| `reverse-string` | Reverse the contents of `input.txt` into `output.txt` |

You can run any one directly through Harbor to see what the pipeline wraps:

```bash
harbor run -p datasets/mini_harbor/create-file -a oracle
```

## Running remotely and at scale

The folder is named `rlft_harbor_daytona` for a reason: the remote-execution
story is [Daytona](https://www.daytona.io/). When you set `env_provider: daytona`
in a config, Harbor launches each task in a Daytona sandbox instead of local
Docker. This matters when your ZenML steps run somewhere without a usable Docker
daemon — for example on a Kubernetes orchestrator — because Daytona removes the
need for Docker-in-Docker.

When the pipeline runs remotely, the orchestrator pod needs the relevant API
keys. The `--forward-env` flag copies your local `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, and `DAYTONA_API_KEY` into the remote step environment:

```bash
python run.py --config configs/prod.yaml --forward-env
```

**A real warning about concurrency.** Parallelism multiplies across two layers.
ZenML fans out one job per matrix entry, and Harbor's `-n` runs that many trials
in parallel *inside* each job. A 12-entry matrix at `n_concurrent: 50` is 600
sandboxes running at once — a great demo and a genuinely surprising bill. Keep
both numbers modest until you know what a run costs.

## The "build once" pattern (where ZenML earns its keep next)

There's an efficiency trap worth naming. As it stands, each `run_harbor_job`
branch calls `harbor run` independently in its own temp directory. If your matrix
has twelve branches and they all evaluate the same tasks, Harbor builds the same
task container images **twelve times**. You pay the build cost on every branch.

A ZenML DAG is the natural home for the fix: a single *central preparation step*
that builds each task's image once (or warms a Daytona snapshot once), publishes
the references as an artifact, and lets every eval branch reuse them. Sketch:

```python
@step(enable_cache=True)              # built once, reused on every later run
def prepare_environments(dataset_path: str) -> EnvManifest:
    # Build each task image once, push to a registry / warm a snapshot,
    # and return references the eval branches can point Harbor at.
    ...

@pipeline(dynamic=True)
def harbor_eval_campaign(config_path: str = "configs/dev.yaml"):
    matrix = build_matrix(config_path=config_path)
    envs = prepare_environments(dataset_path=...)   # one node, all branches depend on it
    for idx in range(len(matrix.load())):
        spec = matrix.chunk(index=idx)
        job = run_harbor_job(spec=spec, envs=envs)  # reuse prebuilt images
        ...
```

With `enable_cache=True` on that step, the build runs on the first campaign and
every subsequent run reuses the cached artifact — turning "rebuild every time"
into "prepare once, evaluate many." Adding it is genuinely small: one extra step
and one dependency edge. The pipeline already fans out and tracks artifacts, so
slotting a shared upstream node in front of the eval branches is a natural,
low-effort extension rather than a rewrite.

## Extending it further

This example is complete and runnable as an eval-campaign tool on its own. But
because everything is already expressed as ZenML steps and artifacts, growing it
into a full agent-improvement loop is mostly a matter of adding steps to the same
pipeline — not re-architecting anything. The loop that closes back on itself
looks like this:

```
Evaluate (Harbor) → Diagnose (ZenML) → Improve (SFT / RLFT) → Re-evaluate (Harbor) → Compare (ZenML)
```

Each new piece is an additive step:

- **Export failure traces** — a step that runs Harbor's trace export over the
  failing trials, producing an SFT-ready dataset artifact.
- **Train on the failures** — a GPU-enabled step that fine-tunes on that dataset,
  or turns failing tasks into trainable environments via Prime Intellect's
  [`verifiers`](https://github.com/PrimeIntellect-ai/verifiers) library.
- **Re-evaluate and compare** — feed the improved model back through the same
  `harbor_eval_campaign` and diff the new leaderboard against the old one.

The payoff of doing it this way is lineage: an eval failure links to the training
run, which links to the improved model, which links to its re-eval — all
queryable later. Most teams can run evals; few have that whole loop wired
together reproducibly. The point of this example is that getting there is a series
of small, additive steps on top of what's already here.

## Project structure

| Path | Purpose |
|------|---------|
| `run.py` | CLI entry point (`--config`, `--forward-env`) |
| `pipelines/harbor_eval_campaign.py` | `@pipeline(dynamic=True)` with the fan-out loop |
| `steps/build_matrix.py` | Config → `List[HarborRunSpec]` |
| `steps/run_harbor_job.py` | `HarborRunSpec` → job directory (via subprocess) |
| `steps/parse_harbor_job.py` | Job directory → `JobSummary` (defensive parsing) |
| `steps/build_report.py` | Summaries → `CampaignReport` + HTML |
| `models/harbor_models.py` | Pydantic data contracts between steps |
| `utils/harbor_cli.py` | `build_harbor_command()`, `find_job_dir()` |
| `configs/` | Campaign YAML configs |
| `datasets/mini_harbor/` | Seven bundled test tasks |
| `data/` | HTML report template and CSS |

## Key ZenML patterns on display

- **`@pipeline(dynamic=True)`** — DAG shape determined at runtime from your
  config. Runs unchanged on the local, local-Docker, Kubernetes, Vertex,
  SageMaker, and AzureML orchestrators.
- **`.load()` then `.chunk(index=idx)`** — `.load()` materializes the matrix list
  just to read its length; `.chunk(index=idx)` then creates a DAG edge per entry
  *without* dragging the data back through the orchestrator.
- **`PathMaterializer`** — built-in directory archiving turns each Harbor job
  folder into a versioned `.tar.gz` artifact, no custom materializer needed.
- **`HTMLString`** — a return type ZenML renders as a visualization directly in
  the dashboard.
- **Pydantic models as step contracts** — `HarborRunSpec`, `JobSummary`, and
  `CampaignReport` give every step boundary validation and a clear typed
  interface.
