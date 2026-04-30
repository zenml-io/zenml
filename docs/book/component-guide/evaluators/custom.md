---
description: Implementing a custom evaluator flavor.
---

# Develop a custom evaluator

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

If none of the built-in [evaluator flavors](evaluators.md#available-flavors) fit your needs — for example, you want to integrate a different judge model, use an internal evaluation service, or write a deterministic scorer — you can implement your own flavor in four steps.

## Step 1: Implement the evaluator

Subclass `BaseEvaluator`, declare which modes your flavor supports via `supported_modes`, and override the corresponding `evaluate_*` methods:

```python
from typing import List, Set

from zenml.evaluators.base_evaluator import BaseEvaluator
from zenml.evaluators.cases import PointwiseCase, Rubric
from zenml.evaluators.result import CaseResult, EvaluationMode, EvaluationResult


class ConstantScoreEvaluator(BaseEvaluator):
    """Returns a constant score of 1.0 for every case. Useful for testing."""

    @property
    def supported_modes(self) -> Set[EvaluationMode]:
        return {EvaluationMode.POINTWISE}

    def evaluate_pointwise(
        self,
        cases: List[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        case_results = [
            CaseResult(
                case_id=str(i),
                scores={"score": 1.0},
                passed=True,
            )
            for i, _ in enumerate(cases)
        ]
        return EvaluationResult(
            evaluator="constant",
            mode=EvaluationMode.POINTWISE,
            suite_name="",   # set by the step wrapper
            cases=case_results,
            aggregates={},   # recomputed by the step wrapper
        )
```

## Step 2: Define the config

Subclass `BaseEvaluatorConfig` and add any fields your flavor needs. Because `BaseEvaluatorConfig` extends `StackComponentConfig` (a Pydantic model), you can use standard Pydantic validators and `Field` descriptors:

```python
from zenml.evaluators.base_evaluator import BaseEvaluatorConfig


class ConstantScoreEvaluatorConfig(BaseEvaluatorConfig):
    """No additional configuration needed for the constant scorer."""
```

## Step 3: Define the flavor

Subclass `BaseEvaluatorFlavor` and wire the name, config class, and implementation class together. The implementation class is imported lazily inside the `implementation_class` property so that heavy dependencies are not pulled in on flavor registration:

```python
from typing import Type

from zenml.evaluators.base_evaluator import BaseEvaluatorFlavor
from zenml.stack import StackComponent


class ConstantScoreEvaluatorFlavor(BaseEvaluatorFlavor):
    @property
    def name(self) -> str:
        return "constant"

    @property
    def config_class(self) -> Type[ConstantScoreEvaluatorConfig]:
        return ConstantScoreEvaluatorConfig

    @property
    def implementation_class(self) -> Type[StackComponent]:
        # Import lazily to keep flavor registration dependency-free.
        from my_package.constant_evaluator import ConstantScoreEvaluator

        return ConstantScoreEvaluator
```

## Step 4: Register the flavor

Point ZenML at your flavor class using dot notation from the root of your repository (the directory where you ran `zenml init`):

```shell
zenml evaluator flavor register my_package.constant_evaluator_flavor.ConstantScoreEvaluatorFlavor
```

Verify it appears:

```shell
zenml evaluator flavor list
```

You can then register a stack component using the new flavor:

```shell
zenml evaluator register my_constant_evaluator --flavor=constant
```

{% hint style="warning" %}
ZenML resolves the flavor class starting from the directory where `zenml init` was run. Make sure your package is importable from that root, or initialize ZenML at the root of your repository.
{% endhint %}

## Integration flavors

If you are building an integration that will live inside the ZenML repository (or a ZenML-compatible integration package), register your flavor in the integration's `flavors()` classmethod:

```python
from zenml.integrations.integration import Integration


class MyEvalIntegration(Integration):
    NAME = "my_eval"
    REQUIREMENTS = ["my-eval-library>=1.0"]

    @classmethod
    def flavors(cls):
        from my_package.constant_evaluator_flavor import (
            ConstantScoreEvaluatorFlavor,
        )

        return [ConstantScoreEvaluatorFlavor]
```

This makes the flavor available automatically when users run `zenml integration install my_eval`.

## Design considerations

* **Keep the flavor file dependency-free.** The config class and flavor class are loaded on `zenml evaluator register` and `zenml stack register`, even in environments where the actual evaluation library is not installed. Import heavy dependencies only inside `implementation_class` and the evaluator methods.
* **Raise `EvaluationModeNotSupportedError` for unsupported modes.** The base class does this automatically for any method you do not override, so you only need to implement the methods for modes listed in `supported_modes`.
* **Leave `suite_name` and `aggregates` empty in `EvaluationResult`.** The `evaluate_*` step wrappers in `zenml.evaluators.steps` set these fields after calling your evaluator, so you do not need to populate them inside the evaluator itself.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
