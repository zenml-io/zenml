"""Canned completions for the dry-run stub generator.

Four quality tiers, cycled by rollout index so that every GRPO group
contains reward variance (without variance, advantages are all zero and
the training step is a no-op — see BREAKAGE_LOG.md entry 3):

    0: PERFECT      — a correct solution for the specific task (1.0)
    1: RUNS_WRONG   — valid pipeline (wrapped in markdown fences, which
                      the generation layer strips), green run, wrong
                      result (0.7 + partial spec)
    2: RUNTIME_FAIL — parses and imports, crashes when executed (0.3)
    3: SYNTAX_ERROR — not even Python (0.0)

PERFECT completions exist only for the tasks the dry run uses; asking the
stub for a task without one raises, on purpose, rather than silently
degrading the dry-run signal.
"""

# Deliberately wrapped in markdown fences: small models add them no
# matter what the prompt says, so the dry run must exercise the
# fence-stripping path (prompts.strip_markdown_fences) end-to-end. The
# reward is computed on the stripped program; training uses the raw
# tokens including the fences.
RUNS_WRONG = '''\
```python
from zenml import step, pipeline

@step
def wrong_answer() -> int:
    return 999999

@pipeline(dynamic=True)
def generated_pipeline():
    wrong_answer()

if __name__ == "__main__":
    generated_pipeline()
```
'''

RUNTIME_FAIL = '''\
from zenml import step, pipeline

@step
def divide() -> float:
    return 1 / 0

@pipeline(dynamic=True)
def generated_pipeline():
    divide()

if __name__ == "__main__":
    generated_pipeline()
'''

SYNTAX_ERROR = '''\
from zenml import step, pipeline

@step
def broken( -> int:
    return 7
'''

PERFECT = {
    "const_seven": '''\
from zenml import step, pipeline

@step
def make_seven() -> int:
    return 7

@pipeline(dynamic=True)
def seven_pipeline():
    make_seven()

if __name__ == "__main__":
    seven_pipeline()
''',
    "two_step_double": '''\
from zenml import step, pipeline

@step
def start() -> int:
    return 21

@step
def double(x: int) -> int:
    return x * 2

@pipeline(dynamic=True)
def double_pipeline():
    value = start()
    double(value)

if __name__ == "__main__":
    double_pipeline()
''',
    "map_double_sum": '''\
from zenml import step, pipeline

@step
def numbers() -> list[int]:
    return [1, 2, 3, 4]

@step
def double(x: int) -> int:
    return x * 2

@step
def total(values: list[int]) -> int:
    return sum(values)

@pipeline(dynamic=True)
def map_double_pipeline():
    nums = numbers()
    doubled = double.map(nums)
    total(doubled)

if __name__ == "__main__":
    map_double_pipeline()
''',
}

CYCLE = ["perfect", "runs_wrong", "runtime_fail", "syntax_error"]


def canned_completion(task_id: str, rollout_index: int) -> str:
    """Return the canned completion for a (task, rollout) pair.

    Args:
        task_id: Task identifier from tasks.jsonl.
        rollout_index: Position within the GRPO group; selects the tier.

    Returns:
        Python source text, as if the model had produced it.

    Raises:
        KeyError: If a perfect completion is needed but not canned for
            this task.
    """
    tier = CYCLE[rollout_index % len(CYCLE)]
    if tier == "perfect":
        if task_id not in PERFECT:
            raise KeyError(
                f"No canned perfect completion for task '{task_id}'. "
                f"Dry-run tasks must be one of: {sorted(PERFECT)}"
            )
        return PERFECT[task_id]
    if tier == "runs_wrong":
        return RUNS_WRONG
    if tier == "runtime_fail":
        return RUNTIME_FAIL
    return SYNTAX_ERROR
