"""Agentic human-in-the-loop workflow using ZenML dynamic pipelines."""

import argparse
from typing import Annotated

import pandas as pd

from zenml import pipeline, step, wait
from zenml.config import DockerSettings


@step
def plan_agent_tasks(
    goal: str,
) -> Annotated[list[dict[str, str]], "agent_tasks"]:
    """Create the task list that the agent workflow will execute."""
    return [
        {
            "task_id": "research",
            "instruction": f"Research constraints for: {goal}",
            "tool": "search",
        },
        {
            "task_id": "draft",
            "instruction": f"Draft a candidate plan for: {goal}",
            "tool": "planner",
        },
        {
            "task_id": "risk_check",
            "instruction": f"Identify risks before acting on: {goal}",
            "tool": "reviewer",
        },
    ]


@step(runtime="isolated")
def execute_agent_task(
    task: dict[str, str],
) -> Annotated[pd.DataFrame, "task_trace"]:
    """Execute one planned task and return a tabular trace."""
    return pd.DataFrame(
        [
            {
                "task_id": task["task_id"],
                "tool": task["tool"],
                "instruction": task["instruction"],
                "result": f"Completed {task['task_id']} with {task['tool']}",
                "confidence": 0.82 if task["task_id"] == "risk_check" else 0.9,
            }
        ]
    )


@step
def summarize_agent_work(
    results: list[pd.DataFrame],
) -> Annotated[pd.DataFrame, "agent_summary"]:
    """Combine mapped task results into a single summary."""
    return pd.concat(results, ignore_index=True)


@step
def finalize_decision(
    summary: pd.DataFrame, approved: bool
) -> Annotated[pd.DataFrame, "decision_record"]:
    """Act on the human decision: deploy when approved, record rejection otherwise."""
    if approved:
        action, status = "deploy_agent_recommendation", "completed"
    else:
        action, status = "skip_agent_recommendation", "rejected"
    return pd.DataFrame(
        [
            {
                "action": action,
                "status": status,
                "reviewed_tasks": len(summary),
            }
        ]
    )


docker = DockerSettings(
    requirements=[
        "pandas>=2.0",
    ],
)


@pipeline(dynamic=True, enable_cache=False, settings={"docker": docker})
def agentic_hitl_pipeline(
    goal: str = "prepare an agent workflow for production",
) -> None:
    """Fan out agent tasks, pause for approval, then conditionally act."""
    tasks = plan_agent_tasks(goal=goal)
    task_results = execute_agent_task.map(task=tasks)
    summary = summarize_agent_work(task_results)

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


def main() -> None:
    """Run the example pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--goal",
        default="prepare an agent workflow for production",
        help="Goal used to plan the agent tasks.",
    )
    args = parser.parse_args()
    agentic_hitl_pipeline(goal=args.goal)


if __name__ == "__main__":
    main()
