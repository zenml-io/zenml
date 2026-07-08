"""Prompt construction for the RL spike.

The system prompt contains a deliberately slim cheatsheet of the ZenML
dynamic-pipelines API. The policy model (a small Qwen) has never seen this
API — dynamic pipelines postdate its training data — so the cheatsheet is
the only source it can learn the API from. Keeping it slim is part of the
task difficulty: the model must generalize from a few patterns, not copy a
manual.
"""

CHEATSHEET = """\
You write ZenML dynamic pipelines. Quick reference:

```python
from zenml import step, pipeline

@step
def make_numbers() -> list[int]:
    return [1, 2, 3]

@step
def double(x: int) -> int:
    return x * 2

@step
def total(values: list[int]) -> int:
    return sum(values)

@pipeline(dynamic=True)
def my_pipeline():
    numbers = make_numbers()          # returns an artifact handle, not data
    doubled = double.map(numbers)     # fan out: one step per element
    total(doubled)                    # a step can take the mapped results as a list

if __name__ == "__main__":
    my_pipeline()
```

Rules:
- Every function used in the pipeline body must be a `@step`. Steps must have
  type hints on parameters and return values.
- The pipeline function must be decorated with `@pipeline(dynamic=True)`.
- Inside the pipeline body, calling a step returns an artifact handle. Pass
  handles directly to downstream steps to connect them.
- To use an artifact's VALUE in Python control flow (if/for), call `.load()`
  on it: `n = count_step().load()`. Only do this for control flow; for data
  flow, pass the handle.
- `some_step.map(seq_artifact)` runs the step once per element of a
  sequence-output artifact. The mapped result can be passed to a step that
  accepts `list[...]`.
- `some_step.product(a=art1, b=art2)` runs the step for every combination
  of elements (cartesian product).
- Steps take literal Python values as parameters too: `double(x=5)` is valid.
- The script must run the pipeline when executed:
  `if __name__ == "__main__": my_pipeline()`.
"""

SYSTEM_PROMPT = (
    CHEATSHEET
    + """
Respond with a single complete Python file and nothing else. No explanations,
no markdown fences — just Python source code that can be saved to a file and
executed directly.
"""
)


def build_prompt(task_prompt: str) -> list[dict[str, str]]:
    """Build the chat messages for one task.

    Args:
        task_prompt: The task description ("Write a ZenML dynamic pipeline
            that ...").

    Returns:
        Chat messages in the OpenAI format that both vLLM's chat API and
        the tokenizer's chat template accept.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt},
    ]


def strip_markdown_fences(completion: str) -> str:
    """Remove ```python fences if the model added them despite instructions.

    Small models frequently wrap code in fences no matter what the system
    prompt says. Stripping them is generation-side leniency, not reward
    leniency: we score the code the model *meant* to write. The reward
    function never sees the fences.

    Args:
        completion: Raw model completion text.

    Returns:
        The completion with a single leading/trailing code fence removed.
    """
    text = completion.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    return text.strip() + "\n"
