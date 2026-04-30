---
description: Evaluating LLM outputs with an OpenAI model as judge.
---

# OpenAI Evaluator

The OpenAI Evaluator is an [Evaluator](evaluators.md) flavor provided with the OpenAI ZenML integration. It uses an OpenAI chat model as an LLM-as-judge to score pipeline outputs across all three evaluation modes: POINTWISE, REFERENCE, and RAG.

## When would you want to use it?

You should use the OpenAI Evaluator when:

* Your team already uses OpenAI models in production and wants a consistent judge for evaluating outputs.
* You need a quick, configuration-light way to add quality gates to a pipeline without standing up additional infrastructure.
* You want to evaluate multiple modes (pointwise, reference, and RAG) with a single registered stack component.

Consider the [Ragas Evaluator](ragas.md) if you prefer framework-managed RAG metrics with well-defined scoring semantics, or the [custom evaluator guide](custom.md) if you need to integrate a different provider.

## Installation

The OpenAI Evaluator is provided by the `openai` ZenML integration. Install it alongside ZenML:

```shell
pip install "zenml[openai]"
```

Or via the ZenML CLI:

```shell
zenml integration install openai -y
```

## How do you configure it?

### Store your API key securely

Store your OpenAI API key as a ZenML secret so it is never committed to configuration files:

```shell
zenml secret create openai_creds --OPENAI_API_KEY=<your-api-key>
```

### Register the evaluator

```shell
zenml evaluator register my_openai_evaluator \
    --flavor=openai \
    --model=gpt-4o-mini \
    --api_key_secret=openai_creds
```

Add it to a stack:

```shell
zenml stack update my_stack --evaluator=my_openai_evaluator
```

If you prefer to use the `OPENAI_API_KEY` environment variable directly (for local development), omit `--api_key_secret` and set the variable in your environment:

```shell
export OPENAI_API_KEY=<your-api-key>

zenml evaluator register my_openai_evaluator \
    --flavor=openai \
    --model=gpt-4o-mini
```

{% hint style="warning" %}
Storing credentials directly in stack component configuration is not recommended for shared or production stacks. Use ZenML secrets (`--api_key_secret`) so that the key is resolved at runtime and never stored in plain text.
{% endhint %}

## Pipeline example

The following pipeline runs a pointwise evaluation and gates the run if the score drops below a baseline:

```python
from typing import List

from zenml import pipeline, step
from zenml.evaluators import (
    BaselineSpec,
    PointwiseCase,
    Rubric,
    evaluate_pointwise,
)


@step
def build_cases() -> List[PointwiseCase]:
    return [
        PointwiseCase(
            input="Explain gradient descent in one sentence.",
            output="Gradient descent is an optimization algorithm that "
                   "iteratively adjusts parameters in the direction that "
                   "reduces a loss function.",
        ),
    ]


@pipeline
def pointwise_eval_pipeline() -> None:
    cases = build_cases()
    rubric = Rubric(
        name="clarity",
        criterion="Is the explanation clear and accurate for a non-expert?",
        scale=(1, 5),
    )
    evaluate_pointwise(
        cases=cases,
        rubric=rubric,
        suite_name="clarity-v1",
        baseline=BaselineSpec(
            strategy="model_registry",
            model_name="my-llm",
        ),
        on_regression="fail",
        pass_thresholds={"score": 3.0},
        regression_tolerance=0.5,
    )
```

Run it with:

```shell
python run.py
```

## Configuration reference

All fields are set during `zenml evaluator register` (or updated with `zenml evaluator update`).

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `model` | `str` | `gpt-4o-mini` | OpenAI chat model used as judge. Must support structured JSON output (`response_format`). Examples: `gpt-4o`, `gpt-4o-mini`. |
| `temperature` | `float` | `0.0` | Sampling temperature. `0.0` minimizes variance for reproducible evaluation. |
| `max_concurrency` | `int` | `4` | Maximum concurrent requests to OpenAI when evaluating multiple cases. |
| `api_key_secret` | `str` or `None` | `None` | Name of a ZenML secret that holds `OPENAI_API_KEY`. If unset, the `OPENAI_API_KEY` environment variable is used. |

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
