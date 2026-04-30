---
description: Evaluating RAG pipelines with the Ragas framework.
---

# Ragas Evaluator

The Ragas Evaluator is an [Evaluator](evaluators.md) flavor provided with the Ragas ZenML integration. It wraps the [Ragas](https://docs.ragas.io) evaluation framework to compute RAG-specific metrics such as faithfulness and answer relevance, as well as reference-based metrics for comparing outputs to expected answers.

## When would you want to use it?

You should use the Ragas Evaluator when:

* You are running a retrieval-augmented generation (RAG) pipeline and want standardized metrics with well-defined semantics backed by the Ragas framework.
* You want reference-based evaluation using Ragas's semantic similarity metrics rather than a hand-crafted LLM-as-judge prompt.
* Your team already uses Ragas in notebooks or scripts and wants to promote those evaluations into automated pipeline gates.

The Ragas Evaluator supports **RAG** and **REFERENCE** modes only. It does not support POINTWISE mode. If you need pointwise evaluation, use the [OpenAI Evaluator](openai.md) instead.

{% hint style="info" %}
Ragas relies on a judge model under the hood — typically an OpenAI model — to compute several of its metrics. You will still need an `OPENAI_API_KEY` environment variable (or equivalent credentials for another provider) available in the environment where the pipeline runs.
{% endhint %}

{% hint style="warning" %}
Ragas is a young library with a fast-moving API. ZenML's integration pins to `ragas>=0.2,<0.4`. If you see import errors after updating Ragas, check whether you are within the supported range.
{% endhint %}

## Installation

The Ragas Evaluator is provided by the `ragas` ZenML integration:

```shell
pip install "zenml[ragas]"
```

Or via the ZenML CLI:

```shell
zenml integration install ragas -y
```

## How do you configure it?

### Register the evaluator

```shell
zenml evaluator register my_ragas_evaluator \
    --flavor=ragas \
    --judge_model_provider=openai \
    --judge_model=gpt-4o-mini
```

Add it to a stack:

```shell
zenml stack update my_stack --evaluator=my_ragas_evaluator
```

Because Ragas picks up credentials from the environment rather than from the stack component config, set `OPENAI_API_KEY` in the environment where the pipeline runs (or use a ZenML secret at the orchestrator level).

## Pipeline example

```python
from typing import List

from zenml import pipeline, step
from zenml.evaluators import (
    BaselineSpec,
    RAGCase,
    evaluate_rag,
)


@step
def build_rag_cases() -> List[RAGCase]:
    return [
        RAGCase(
            query="What causes the northern lights?",
            context=[
                "The aurora borealis is caused by charged solar particles "
                "interacting with Earth's magnetic field and atmosphere."
            ],
            response="The northern lights are caused by charged particles "
                     "from the sun colliding with atmospheric gases near "
                     "Earth's poles.",
            expected_answer="Solar particles interacting with Earth's magnetic field.",
        ),
    ]


@pipeline
def ragas_eval_pipeline() -> None:
    cases = build_rag_cases()
    evaluate_rag(
        cases=cases,
        metrics=["faithfulness", "answer_relevance"],
        suite_name="rag-ragas-v1",
        baseline=BaselineSpec(
            strategy="model_registry",
            model_name="my-rag-model",
        ),
        on_regression="fail",
        pass_thresholds={"faithfulness": 0.8},
    )
```

## Configuration reference

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `judge_model_provider` | `str` | `openai` | LLM provider Ragas uses as judge. Examples: `openai`, `anthropic`. |
| `judge_model` | `str` | `gpt-4o-mini` | Specific model identifier within the provider. Example: `gpt-4o-mini` for OpenAI. |
| `embedding_model` | `str` or `None` | `None` | Embedding model for similarity-based Ragas metrics. Example: `text-embedding-3-small`. When `None`, Ragas uses its built-in default for the provider. |

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
