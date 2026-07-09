"""GEPAAdapter wiring the spike's generate → sandbox-score path into gepa.

The candidate has exactly one component, "cheatsheet": the evolvable system
prompt from the parent example's prompts.py. evaluate() is the GRPO loop's
first two steps under a different name; the verifier inside the sandbox is
byte-identical. What GEPA adds over GRPO is that the scorer's reward JSON
(breakdown, spec clauses, error, run output tail) is *read* by a reflection
LM instead of being collapsed into a scalar.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from generation import Generator
from gepa import EvaluationBatch, GEPAAdapter
from scoring import score_program

# One sandbox session per episode, a few in flight: the local flavor takes
# ~6s per episode serially; 4 workers keeps a 12-task eval under ~30s
# without re-entering the fan-out/429 territory of BREAKAGE_LOG 12/15.
MAX_PARALLEL_EPISODES = 4

Task = Dict[str, Any]  # one tasks.jsonl record: id, prompt, spec
Trajectory = Dict[str, Any]
Output = Dict[str, Any]


def build_feedback(trajectory: Trajectory) -> str:
    """Render one episode's scorer verdict as text for the reflection LM.

    This string is the information channel between the sandbox verifier and
    the reflection model — the thing GRPO discarded. It should tell the
    reflection LM enough to diagnose WHY the cheatsheet failed this task:
    which reward components were missed (breakdown), which spec clauses
    failed (spec_clauses), the scorer's error verdict, and the generated
    pipeline's own crash output (run_output_tail) when there is one.

    Args:
        trajectory: One episode dict with keys: task (the tasks.jsonl
            record), completion_text (raw model output), program_text
            (fence-stripped code that ran), score (the reward dict from
            scoring.score_program: reward, breakdown, spec_clauses, error,
            run_output_tail, infra_error).

    Returns:
        A feedback string for the reflection prompt.
    """
    score = trajectory["score"]

    # Harness sickness is not the model's fault: tell the reflection LM to
    # ignore the episode entirely rather than "fix" a non-cheatsheet cause.
    if score["infra_error"]:
        return (
            "DISREGARD THIS EPISODE: the scoring infrastructure failed "
            f"({score['infra_error']}). The generated code was never judged."
        )

    lines = [f"Total reward: {score['reward']} out of 1.0."]

    breakdown = score["breakdown"]
    if breakdown.get("parse_import", 0) == 0:
        lines.append(
            "The code failed the most basic gate: it has a syntax error "
            "or crashes on import."
        )
    elif breakdown.get("runs_green", 0) == 0:
        lines.append(
            "The code parses and imports, but executing it did not produce "
            "a completed pipeline run."
        )

    failed = [name for name, ok in score["spec_clauses"].items() if not ok]
    passed = [name for name, ok in score["spec_clauses"].items() if ok]
    if failed:
        lines.append(f"Failed requirement checks: {', '.join(failed)}.")
    if passed:
        lines.append(f"Passed requirement checks: {', '.join(passed)}.")

    if score["error"]:
        lines.append(f"Scorer verdict: {score['error']}.")

    # The traceback is the highest-signal diagnosis material, but only on
    # failure, and capped so 3-5 records still fit one reflection prompt.
    if score["reward"] < 1.0 and score["run_output_tail"]:
        lines.append(
            "Output tail of the executed code:\n"
            + score["run_output_tail"][-600:]
        )

    if score["reward"] == 1.0:
        lines.append(
            "Perfect episode — whatever cheatsheet guidance produced this "
            "should be preserved."
        )
    return "\n".join(lines)


class CheatsheetAdapter(GEPAAdapter):
    """Evaluate cheatsheet candidates via hosted-API generation + sandbox scoring."""

    def __init__(self, generator: Generator) -> None:
        """Store the generation function (real API or dry-run stub).

        Args:
            generator: (cheatsheet, task_prompt) -> (completion_text,
                program_text).
        """
        self._generator = generator

    def _run_episode(
        self, cheatsheet: str, task: Task
    ) -> "tuple[Output, float, Trajectory]":
        """One task under one candidate; never raises (gepa's contract)."""
        try:
            completion_text, program_text = self._generator(
                cheatsheet, task["prompt"]
            )
            score = score_program(program_text, task["spec"])
        except Exception as e:
            completion_text, program_text = "", ""
            score = {
                "reward": 0.0,
                "breakdown": {},
                "spec_clauses": {},
                "error": None,
                "run_output_tail": "",
                "infra_error": f"{type(e).__name__}: {e}",
                "timings": {},
            }
        output = {
            "task_id": task["id"],
            "program_text": program_text,
            "reward": score["reward"],
            "infra_error": score["infra_error"],
        }
        trajectory = {
            "task": task,
            "completion_text": completion_text,
            "program_text": program_text,
            "score": score,
        }
        return output, score["reward"], trajectory

    def evaluate(
        self,
        batch: List[Task],
        candidate: Dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Run every task in the batch under the candidate cheatsheet.

        Args:
            batch: Task records to evaluate.
            candidate: {"cheatsheet": <text>}.
            capture_traces: Whether to keep per-episode trajectories for
                the reflection dataset.

        Returns:
            EvaluationBatch with one output/score (and trajectory when
            requested) per task, in batch order.
        """
        cheatsheet = candidate["cheatsheet"]
        with ThreadPoolExecutor(MAX_PARALLEL_EPISODES) as pool:
            episodes = list(
                pool.map(
                    lambda task: self._run_episode(cheatsheet, task), batch
                )
            )
        outputs = [episode[0] for episode in episodes]
        scores = [episode[1] for episode in episodes]
        trajectories = (
            [episode[2] for episode in episodes] if capture_traces else None
        )
        return EvaluationBatch(
            outputs=outputs, scores=scores, trajectories=trajectories
        )

    def make_reflective_dataset(
        self,
        candidate: Dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Turn episode trajectories into the reflection LM's evidence.

        Args:
            candidate: The evaluated candidate (unused; the cheatsheet text
                is already in the reflection prompt via gepa).
            eval_batch: Result of evaluate(..., capture_traces=True).
            components_to_update: Always ["cheatsheet"] here (single
                component).

        Returns:
            {"cheatsheet": [one record per episode]} in gepa's recommended
            Inputs / Generated Outputs / Feedback schema.
        """
        records = [
            {
                "Inputs": {"task": trajectory["task"]["prompt"]},
                "Generated Outputs": trajectory["completion_text"],
                "Feedback": build_feedback(trajectory),
                "score": trajectory["score"]["reward"],
            }
            for trajectory in (eval_batch.trajectories or [])
        ]
        return {component: records for component in components_to_update}
