---
description: Evaluating LLM outputs and gating pipeline runs on quality regressions.
icon: magnifying-glass-chart
---

# Evaluators

Evaluators are a first-class stack component in ZenML designed to assess the quality of LLM outputs within ML pipelines. Where experiment trackers log metrics for human review, evaluators score outputs automatically and can block a pipeline run if quality drops below an established baseline. This makes LLM evaluation a gate in your CI/CD-style pipeline rather than an afterthought.

Related concepts:

* The Evaluator is an optional stack component registered as part of your ZenML [Stack](https://docs.zenml.io/user-guides/production-guide/understand-stacks).
* Evaluation results are persisted as typed artifacts in the [Artifact Store](https://docs.zenml.io/stacks/artifact-stores/) and can be linked to model versions in the [Model Registry](../model-registries/README.md) to serve as baselines for future runs.

## Evaluation modes

The evaluator framework provides three evaluation modes, each suited to a different scenario.

### Pointwise

Pointwise evaluation scores a single (input, output) pair against a rubric — essentially an LLM-as-judge setup. You define a `Rubric` with a criterion, a numeric scale, and optional worked examples; the evaluator asks the judge model to assign a score. Use this when you have no reference answer and want to assess qualities like coherence, helpfulness, or safety.

Example use case: you deploy a new prompt template for a customer-support assistant and want to verify that response quality does not drop compared to the previous template.

### Reference

Reference evaluation compares a model's actual output to a known expected output. The evaluator scores semantic equivalence rather than exact string match, so paraphrases score well. Use this for regression testing of deterministic tasks such as classification, summarization, or translation where gold labels exist.

Example use case: after fine-tuning a model you run it against a held-out labeled dataset and verify that accuracy has not regressed below the production model's level.

### RAG

RAG evaluation scores retrieval-augmented generation triples: a query, a list of retrieved context passages, and a generated response. Metrics typically include faithfulness (does the response stay grounded in the context?), answer relevance (does the response address the query?), and context relevance. Use this when you are maintaining a RAG system and want to catch regressions caused by changes to the retrieval component or the generation model.

Example use case: after updating your vector store index you run a RAG eval suite to confirm that faithfulness and answer relevance scores remain at or above the baseline produced by the previous index.

## Baseline and gate semantics

Every `evaluate_*` step accepts an optional `baseline` parameter (`BaselineSpec`) and an `on_regression` parameter. After the evaluator scores the current suite, the step compares aggregate metrics against the resolved baseline. If any metric drops by more than `regression_tolerance`, a regression is detected and the gate fires.

`on_regression` accepts three values:

* `"fail"` — raises `EvaluationRegressionError`, which fails the pipeline step. This is the recommended setting for production pipelines.
* `"warn"` — logs a warning but allows the run to continue.
* `"trigger"` — currently logs the regression payload at INFO level. A general event-dispatch API for routing this into the ZenML trigger system is planned as a future enhancement (see [#4787](https://github.com/zenml-io/zenml/discussions/4787)); for now, treat `"trigger"` as equivalent to `"warn"`.

Baselines are resolved through a `BaselineSpec`:

* `strategy="model_registry"` (default) — finds the latest `EvaluationResult` artifact linked to the production model version in the active stack's model registry. Fails gracefully (no regression check) if no registry is configured or no production version exists.
* `strategy="explicit"` — loads a specific `EvaluationResult` artifact by UUID.
* `strategy="none"` — skips the baseline comparison entirely.

## Available flavors

| Evaluator | Flavor | Integration | Supported modes |
| --------- | ------ | ----------- | --------------- |
| [OpenAI](openai.md) | `openai` | `openai` | POINTWISE, REFERENCE, RAG |
| [Ragas](ragas.md) | `ragas` | `ragas` | RAG, REFERENCE |
| [Custom](custom.md) | _custom_ | | _any_ |

To list available flavors:

```shell
zenml evaluator flavor list
```

## Registering an evaluator

Evaluators follow the same registration pattern as all other stack components. For example, to add an OpenAI-backed evaluator:

```shell
# Store your API key as a ZenML secret
zenml secret create openai_creds --OPENAI_API_KEY=<your-key>

# Register the evaluator
zenml evaluator register my_evaluator \
    --flavor=openai \
    --model=gpt-4o-mini \
    --api_key_secret=openai_creds

# Add it to your stack
zenml stack update my_stack --evaluator=my_evaluator
```

## Using an evaluator in a pipeline

The `evaluate_rag`, `evaluate_reference`, and `evaluate_pointwise` functions in `zenml.evaluators` are pre-built `@step`s. Drop them directly into a pipeline:

```python
from typing import List

from zenml import pipeline, step
from zenml.evaluators import (
    RAGCase,
    BaselineSpec,
    evaluate_rag,
)


@step
def build_rag_cases() -> List[RAGCase]:
    return [
        RAGCase(
            query="What is the boiling point of water?",
            context=["Water boils at 100 degrees Celsius at sea level."],
            response="Water boils at 100 °C.",
        ),
    ]


@pipeline
def rag_eval_pipeline() -> None:
    cases = build_rag_cases()
    evaluate_rag(
        cases=cases,
        metrics=["faithfulness", "answer_relevance"],
        suite_name="rag-v1",
        baseline=BaselineSpec(strategy="model_registry", model_name="my-rag-model"),
        on_regression="fail",
        pass_thresholds={"faithfulness": 0.8, "answer_relevance": 0.7},
    )
```

The step emits an `EvaluationResult` artifact that ZenML persists automatically. When this artifact is linked to a model version in the model registry, it becomes available as a baseline for the next run.

## Model registry integration

`BaselineSpec(strategy="model_registry", model_name="my-rag-model")` resolves the baseline by finding the most recent `EvaluationResult` artifact (matching `suite_name` and `mode`) that is linked to the production version of `my-rag-model` in the active stack's model registry. As long as you promote model versions through the standard ZenML model registry API, baselines update automatically without any configuration changes.

See the [per-flavor pages](openai.md) and the [custom evaluator guide](custom.md) for detailed configuration and extension options.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
