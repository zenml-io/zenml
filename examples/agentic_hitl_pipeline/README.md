# Agentic Human-in-the-Loop Pipeline

Pause an agentic ZenML pipeline for human approval before it takes a final action, using `zenml.wait(...)` inside a dynamic pipeline.

**ZenML version**: 0.94+ (Python 3.10+)

## 🎯 What You'll Learn

- Build a `@pipeline(dynamic=True)` that drives runtime control flow with regular Python
- Fan out mapped work with `step.map(...)` and reduce the results
- Pause a run with `zenml.wait(...)` and branch on the human decision
- Surface a concise approval prompt + a structured report on the dashboard
- Name step outputs with `Annotated` for clean lineage

## 🏃 Quickstart

```bash
pip install -r requirements.txt
zenml init
python run.py
```

When the run pauses, open the dashboard URL printed in the logs and resolve the
`human_approval` wait condition (Continue / Abort).

Pass a custom goal:

```bash
python run.py --goal "prepare a production rollout plan"
```

## 📋 Prerequisites

- Python 3.10 or higher
- A ZenML server (`zenml login --local` for local mode, or `zenml login <tenant>` for ZenML Pro)

## 🏗️ What's Inside

```
📁 agentic_hitl_pipeline/
├── run.py            - Dynamic pipeline + step definitions
├── requirements.txt
└── README.md
```

Four steps, one dynamic pipeline:

- `plan_agent_tasks` → returns the task list (`agent_tasks`)
- `execute_agent_task` → mapped over the task list, returns a per-task trace (`task_trace`)
- `summarize_agent_work` → reduces mapped outputs into a single summary (`agent_summary`)
- `finalize_decision` → runs after approval resolves; deploys on `True`, records rejection on `False` (`decision_record`)

## 🔑 Key Concepts

### Dynamic fan-out + reduce

The planning step returns a list of tasks; `step.map(...)` runs `execute_agent_task` once per task in parallel, then `summarize_agent_work` reduces the mapped outputs:

```python
tasks = plan_agent_tasks(goal=goal)
task_results = execute_agent_task.map(task=tasks)
summary = summarize_agent_work(task_results)
```

### Artifact naming with `Annotated`

Every step output is named so lineage and dashboards stay readable:

```python
from typing import Annotated

@step
def summarize_agent_work(
    results: list[pd.DataFrame],
) -> Annotated[pd.DataFrame, "agent_summary"]:
    return pd.concat(results, ignore_index=True)
```

### Human approval with `zenml.wait(...)`

`wait()` pauses the dynamic pipeline until an external actor resolves the condition. The `question` is a short prompt shown on the wait card; rich context goes into `metadata`, which the dashboard exposes on the Metadata tab.

```python
report = summary.load()
avg_confidence = round(float(report["confidence"].mean()), 3)

approved = wait(
    schema=bool,
    question=(
        f"Approve and deploy? {len(report)} tasks, "
        f"avg confidence {avg_confidence}."
    ),
    metadata={
        "goal": goal,
        "tasks_completed": len(report),
        "avg_confidence": avg_confidence,
        "report": report.to_dict(orient="records"),
    },
    name="human_approval",
)

finalize_decision(summary=summary, approved=approved)
```

If using the Kubernetes orchestrator, `wait(...)` doesn't just block — once the timeout elapses and the tree quiesces, ZenML transitions the run to `PAUSED` and **tears down the orchestration pod** so it stops consuming cluster resources while waiting on the human. When the wait condition is resolved (via UI or CLI), the run is rehydrated and continues from the wait point. This makes long-running approvals practically free.

You can resolve the wait condition from the CLI as well:

```bash
zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
```

### Branching on the decision

`finalize_decision` always runs after the wait resolves; it inspects `approved` and either deploys or records the rejection:

```python
@step
def finalize_decision(
    summary: pd.DataFrame, approved: bool
) -> Annotated[pd.DataFrame, "decision_record"]:
    if approved:
        action, status = "deploy_agent_recommendation", "completed"
    else:
        action, status = "skip_agent_recommendation", "rejected"
    return pd.DataFrame([{"action": action, "status": status, "reviewed_tasks": len(summary)}])
```

Aborting the wait via the dashboard is handled by the framework — it terminates the run; you don't catch it in user code.

### Isolated task execution

`execute_agent_task` uses `runtime="isolated"` so each mapped task can run in its own environment when the orchestrator supports it (e.g. Kubernetes). On the local orchestrator, ZenML logs a warning and falls back to inline execution — useful for trying the example without a remote stack.

```python
@step(runtime="isolated")
def execute_agent_task(
    task: dict[str, str],
) -> Annotated[pd.DataFrame, "task_trace"]:
    ...
```

## 🚀 Run the Example

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize ZenML in this directory**
   ```bash
   zenml init
   ```

3. **Run the pipeline**
   ```bash
   python run.py
   ```

   The logs print a `Dashboard URL for Pipeline Run: ...` line — open it. The run will execute through `summarize_agent_work` and pause on the `human_approval` wait card.

4. **Resolve the wait condition**
   - **Dashboard**: toggle the `Value` switch (True approves and deploys, False rejects), then click **Continue** — or click **Abort** to terminate the run.
   - **CLI** (alternative):
     ```bash
     zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
     ```

5. **Inspect the artifacts** in the dashboard — `agent_tasks`, `task_trace` (one per mapped task), `agent_summary`, and `decision_record` are all named outputs you can drill into.

## 🧪 Customization Ideas

- **Real agents**: Replace the placeholder logic in `execute_agent_task` with calls to your actual agent (LangChain, your own LLM client, etc.). Keep the typed I/O so the rest of the pipeline doesn't change.
- **Structured decisions**: Swap `schema=bool` for a Pydantic model so the human can return richer input — e.g. `DeploymentConfig(environment, replicas, notify_slack)` — and have `finalize_decision` consume it directly.
- **Per-task approval**: Move the `wait(...)` *inside* the map (one wait per task) instead of after `summarize_agent_work`, so the human approves each task before it acts.
- **Run on Kubernetes**: Set the active stack to a Kubernetes orchestrator and observe the pod actually being torn down at the wait point and rehydrated on resume.
- **Add a timeout policy**: Set `timeout=` on `wait(...)` and decide what `finalize_decision` should do if approval times out (e.g. auto-reject).

## 📚 Learn More

- [Dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines)
- [Wait for external input and resume](https://docs.zenml.io/how-to/steps-pipelines/wait_resume)
- [Artifact management with `Annotated`](https://docs.zenml.io/concepts/artifacts)
- [Kubernetes orchestrator](https://docs.zenml.io/stack-components/orchestrators/kubernetes)
