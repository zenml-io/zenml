"""C2: the spike's pipeline-writing task as a `verifiers` environment.

The collision this file exists to probe (framework_breakout.md Track C,
C2): the spike's reward runs *inside* a ZenML Sandbox session where the
generated code executes; verifiers rubric reward functions run in the
eval/trainer process. So the rubric here opens a ZenML Sandbox session
per completion and runs the spike's unmodified `score_pipeline.py`
inside it — whatever happens is the finding.

Composition notes (the actual C2 findings live in ../BREAKAGE_LOG.md and
the C2 section of ../FINDINGS.md; these are the mechanics):

- verifiers scores rollouts concurrently on one asyncio event loop
  (`Rubric.score_group` gathers individual reward funcs). ZenML's
  sandbox session API is synchronous, so the blocking work is pushed
  into a thread via `asyncio.to_thread`, bounded by a semaphore so a
  large eval can't stampede the sandbox backend (BREAKAGE_LOG 12/15:
  unbounded fan-out is exactly how the 429 findings happened).
- verifiers swallows any exception raised by a reward function and
  scores the rollout 0.0 (rubrics/rubric.py, _call_individual_reward_
  func). That silently conflates "bad completion" with "harness broke"
  — the distinction the spike's run_episode step keeps via its
  error/infra_error split. The rubric therefore catches its own
  failures and records them in state["infra_error"] so callers can
  tell the two zeros apart.

Read-only reuse from the parent example (C2 must not edit shared
files): prompts.py for the system prompt and fence stripping,
sandbox_scripts/score_pipeline.py verbatim as the in-sandbox scorer,
and run_episode.py's flavor-agnostic file transport helpers
(loaded by file path because importing the `steps` package would pull
in the torch/vllm steps this venv deliberately lacks).
"""

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import verifiers as vf
from datasets import Dataset
from pydantic import BaseModel

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXAMPLE_DIR))

from prompts import SYSTEM_PROMPT, strip_markdown_fences  # noqa: E402

TASKS_PATH = EXAMPLE_DIR / "tasks" / "tasks.jsonl"
SCORER_PATH = EXAMPLE_DIR / "sandbox_scripts" / "score_pipeline.py"

# One session per completion is the spike's isolation contract; this cap
# bounds how many run at once during a concurrent eval.
MAX_CONCURRENT_SANDBOXES = int(os.environ.get("C2_MAX_SANDBOXES", "4"))


def _load_run_episode() -> ModuleType:
    """Load steps/run_episode.py without importing the steps package.

    Returns:
        The run_episode module (for its _put_file/_get_file transport
        helpers, which encode the flavor workarounds from BREAKAGE_LOG
        entries 4 and 18).
    """
    spec = importlib.util.spec_from_file_location(
        "rl_spike_run_episode", EXAMPLE_DIR / "steps" / "run_episode.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_transport = _load_run_episode()


def completion_text(completion: Any) -> str:
    """Extract the assistant text from a verifiers completion.

    Chat-mode completions are message lists; completion-mode ones are
    plain strings.

    Args:
        completion: The completion object from the rollout state.

    Returns:
        The raw completion text.
    """
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list):
        for message in reversed(completion):
            # Canned C2 states carry plain dicts; the live rollout path
            # (env.evaluate) carries pydantic Message models — normalize
            # to a dict and treat both the same.
            if isinstance(message, BaseModel):
                message = message.model_dump()
            if (
                isinstance(message, dict)
                and message.get("role") == "assistant"
            ):
                content = message.get("content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    )
    raise ValueError(
        f"Cannot extract text from completion: {type(completion)}"
    )


def score_in_zenml_sandbox(program_text: str, spec: dict) -> dict:
    """Run the spike's scorer on one program inside a ZenML Sandbox session.

    Blocking. This is run_episode's happy path with the step machinery
    removed: create session, upload program/spec/scorer, execute the
    scorer, read back reward.json.

    Args:
        program_text: Fence-stripped generated pipeline source.
        spec: The task's declarative spec (tasks.jsonl `spec` field).

    Returns:
        The scorer's reward.json as a dict (reward, breakdown,
        spec_clauses, timings, error).

    Raises:
        RuntimeError: If the stack has no sandbox or the scorer itself
            fails — infrastructure failures, distinct from a bad
            completion (which returns normally with reward 0.0).
    """
    from zenml.client import Client

    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError(
            "Active stack has no sandbox component; run compare_rewards.py "
            "(which bootstraps one) or register one manually."
        )

    with sandbox.create_session(destroy_on_exit=True) as session:
        _transport._put_file(session, program_text, "pipeline.py")
        _transport._put_file(session, json.dumps(spec), "spec.json")
        _transport._put_file(
            session, SCORER_PATH.read_text(), "score_pipeline.py"
        )
        process = session.exec(
            [
                "python",
                "score_pipeline.py",
                "pipeline.py",
                "spec.json",
                "reward.json",
            ]
        )
        output = process.collect()
        if output.exit_code != 0:
            raise RuntimeError(
                f"scorer exited {output.exit_code}: "
                f"{(output.stderr or output.stdout)[-800:]}"
            )
        return json.loads(_transport._get_file(session, "reward.json"))


class ZenMLSandboxRubric(vf.Rubric):
    """Rubric whose single reward function scores inside a ZenML Sandbox."""

    def __init__(self, **kwargs: Any):
        """Initialize the rubric with the sandbox-scoring reward function.

        Args:
            kwargs: Passed through to vf.Rubric.
        """
        super().__init__(**kwargs)
        self._sandbox_semaphore: asyncio.Semaphore | None = None
        self.add_reward_func(self.sandbox_scored_reward)

    def _semaphore(self) -> asyncio.Semaphore:
        # Created lazily so it binds to the event loop that actually
        # runs the eval, not whichever imported the module.
        if self._sandbox_semaphore is None:
            self._sandbox_semaphore = asyncio.Semaphore(
                MAX_CONCURRENT_SANDBOXES
            )
        return self._sandbox_semaphore

    async def sandbox_scored_reward(
        self, completion: Any, info: dict, state: vf.State, **kwargs: Any
    ) -> float:
        """Score one completion by executing it in a ZenML Sandbox.

        Args:
            completion: The model completion (chat messages or string).
            info: Dataset info dict carrying task_id and spec.
            state: Rollout state; enriched with the scorer's full
                result (state["scorer_result"]) or, on harness failure,
                state["infra_error"].
            kwargs: Unused extras injected by the rubric.

        Returns:
            The spike scorer's 0-1 reward; 0.0 on infrastructure
            failure (recorded in state, since verifiers would otherwise
            swallow the exception into an indistinguishable 0.0).
        """
        # Everything sits inside the try: any exception that escapes a
        # reward function gets swallowed by verifiers into a bare 0.0
        # (entry-16 ambiguity), so even completion parsing must record
        # infra_error before returning.
        try:
            program = strip_markdown_fences(completion_text(completion))
            # C2's direct-state path carries the spec as a dict;
            # datasets built by load_environment carry it JSON-encoded
            # (Arrow needs one schema per column, and spec values are
            # heterogeneous — e.g. expected_output.value is int 7 in
            # one task and str 'hello zenml' in another, which
            # Dataset.from_list rejects).
            spec = info.get("spec") or json.loads(info.get("spec_json", "{}"))
            async with self._semaphore():
                reward_data = await asyncio.to_thread(
                    score_in_zenml_sandbox, program, spec
                )
        except Exception as e:
            state["infra_error"] = f"{type(e).__name__}: {e}"
            return 0.0
        state["scorer_result"] = reward_data
        return float(reward_data["reward"])


def load_tasks(tasks_path: Path = TASKS_PATH) -> list[dict]:
    """Read tasks.jsonl into a list of task dicts.

    Args:
        tasks_path: Path to the task file.

    Returns:
        Task dicts with id, prompt, and spec.
    """
    return [
        json.loads(line)
        for line in tasks_path.read_text().splitlines()
        if line.strip()
    ]


def load_environment(
    max_tasks: int | None = None,
    task_ids: list[str] | None = None,
    **kwargs: Any,
) -> vf.SingleTurnEnv:
    """Build the pipeline-writing task as a verifiers SingleTurnEnv.

    Args:
        max_tasks: Optional cap on dataset size (evals are slow: every
            scored completion runs a real ZenML pipeline in a sandbox).
        task_ids: Optional explicit task selection (C1 dataset shards);
            order follows tasks.jsonl, unknown ids are an error.
        kwargs: Passed through to SingleTurnEnv.

    Returns:
        The environment, ready for env.evaluate(...) or training.

    Raises:
        KeyError: If task_ids contains an id not present in tasks.jsonl.
    """
    tasks = load_tasks()
    if task_ids is not None:
        known = {task["id"] for task in tasks}
        missing = set(task_ids) - known
        if missing:
            raise KeyError(f"Unknown task ids: {sorted(missing)}")
        tasks = [task for task in tasks if task["id"] in set(task_ids)]
    if max_tasks is not None:
        tasks = tasks[:max_tasks]
    dataset = Dataset.from_list(
        [
            {
                "question": task["prompt"],
                "answer": "",
                # No "task" column: 0.1.14's rollout path parses it as
                # a JSON task payload and rejects plain string labels
                # ("use info['env_id'] for routing").
                "info": {
                    "task_id": task["id"],
                    "spec_json": json.dumps(task["spec"]),
                },
            }
            for task in tasks
        ]
    )
    return vf.SingleTurnEnv(
        dataset=dataset,
        system_prompt=SYSTEM_PROMPT,
        rubric=ZenMLSandboxRubric(),
        **kwargs,
    )
