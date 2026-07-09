"""Task-LM generation for GEPA candidates: one completion per (cheatsheet, task).

The GRPO spike's generation path (vLLM batch / HTTP, token IDs, logprobs)
is deliberately NOT reused: GEPA needs no tokens and no logprobs, only
text in / text out. What IS reused read-only from the parent example is
the prompt construction convention and the fence-stripping leniency
(prompts.py), so completions are judged by the same rules as the GRPO
baseline.
"""

import os
import threading
from typing import Any, Callable, Dict, Tuple

from reuse import load_rl_spike_module

strip_markdown_fences = load_rl_spike_module(
    "prompts.py"
).strip_markdown_fences

# The response-format instructions from prompts.SYSTEM_PROMPT, kept OUT of
# the evolvable candidate: GEPA mutates the cheatsheet (the knowledge), not
# the output contract (which the scorer depends on).
RESPONSE_INSTRUCTIONS = """
Respond with a single complete Python file and nothing else. No explanations,
no markdown fences — just Python source code that can be saved to a file and
executed directly.
"""

TASK_MODEL = os.environ.get("GEPA_TASK_MODEL", "gpt-5-nano")
REFLECTION_MODEL = os.environ.get("GEPA_REFLECTION_MODEL", "gpt-5.4")

# Generator contract: (cheatsheet, task_prompt) -> (completion_text,
# program_text). completion_text is the raw model output (goes into
# trajectories for reflection); program_text is the fence-stripped code the
# sandbox actually runs — same split as the GRPO episode contract.
Generator = Callable[[str, str], Tuple[str, str]]


class UsageMeter:
    """Thread-safe token/call counter, one per model role.

    Question (c) of the experiment is cost attribution when a second model
    enters the loop: this is where the numbers come from. ZenML sees them
    as step metadata and in the final report artifact.
    """

    def __init__(self) -> None:
        """Start all counters at zero."""
        self._lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def add(self, usage: Any) -> None:
        """Count one API call and its token usage.

        Args:
            usage: The OpenAI response's `usage` object (may be None).
        """
        with self._lock:
            self.calls += 1
            if usage is not None:
                self.prompt_tokens += usage.prompt_tokens or 0
                self.completion_tokens += usage.completion_tokens or 0

    def as_dict(self) -> Dict[str, int]:
        """Snapshot the counters for metadata/report use.

        Returns:
            calls, prompt_tokens, completion_tokens.
        """
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


TASK_USAGE = UsageMeter()
REFLECTION_USAGE = UsageMeter()


def _client():
    from openai import OpenAI

    return OpenAI()  # reads OPENAI_API_KEY / OPENAI_BASE_URL from env


def generate_program(cheatsheet: str, task_prompt: str) -> Tuple[str, str]:
    """One task-LM completion under a candidate cheatsheet.

    Args:
        cheatsheet: The evolvable system-prompt component (the candidate).
        task_prompt: The task description from tasks.jsonl.

    Returns:
        (completion_text, program_text) — raw output and fence-stripped code.
    """
    response = _client().chat.completions.create(
        model=TASK_MODEL,
        messages=[
            {"role": "system", "content": cheatsheet + RESPONSE_INSTRUCTIONS},
            {"role": "user", "content": task_prompt},
        ],
    )
    TASK_USAGE.add(response.usage)
    completion_text = response.choices[0].message.content or ""
    return completion_text, strip_markdown_fences(completion_text)


def reflection_lm(prompt: str) -> str:
    """Reflection-LM callable for gepa.optimize.

    Passed as a callable rather than a model string because the string path
    routes through litellm, which is not a dependency here. This is also
    the cost-attribution point for the second model in the loop.

    Args:
        prompt: gepa's fully-rendered reflection prompt.

    Returns:
        The reflection model's raw text response.
    """
    response = _client().chat.completions.create(
        model=REFLECTION_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    REFLECTION_USAGE.add(response.usage)
    return response.choices[0].message.content or ""


# A syntactically valid single-step pipeline that satisfies the simplest
# tasks (constant outputs) and fails most others — enough reward variance
# to exercise the accept/reject path without any API calls.
_DRY_RUN_PROGRAM = """\
from zenml import step, pipeline


@step
def produce() -> int:
    return 7


@pipeline(dynamic=True)
def my_pipeline():
    produce()


if __name__ == "__main__":
    my_pipeline()
"""


def dry_run_generate(cheatsheet: str, task_prompt: str) -> Tuple[str, str]:
    """Zero-cost generator: canned program, ignores the cheatsheet.

    Proves the plumbing (adapter -> sandbox -> reward JSON -> reflection
    dataset) before any API spend. Reward differences across tasks come
    from the spec clauses, not from generation quality.
    """
    text = _DRY_RUN_PROGRAM
    return text, text


def dry_run_reflection_lm(prompt: str) -> str:
    """Zero-cost reflection: returns a marked cheatsheet mutation.

    gepa's default proposer expects the new component text wrapped in a
    ``` block; it extracts the block content as the new candidate.
    """
    return "```\nYou write ZenML dynamic pipelines. (dry-run mutation)\n```"
