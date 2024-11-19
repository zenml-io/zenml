---
description: Understand how you can name your ZenML artifacts.
---

# How Artifact Naming works in ZenML 

In ZenML pipelines, you often need to reuse the same step multiple times with different inputs, resulting in multiple artifacts. However, the default naming convention for artifacts can make it challenging to track and differentiate between these outputs, especially when they need to be used in subsequent pipelines. Below you can find a detailed exploration of how you might name your output artifacts dynamically or statically, depending on your needs.

ZenML uses type annotations in function definitions to determine artifact names. Output artifacts with the same name are saved with incremented version numbers.

ZenML provides flexible options for naming output artifacts, supporting both static and dynamic naming strategies:
- Names can be generated dynamically at runtime
- Support for lambda functions, callable functions, and string templates
- Compatible with single and multiple output scenarios
- Annotations help define naming strategy without modifying core logic

## Naming Strategies

### Static Naming
Static names are defined directly as string literals.

```python
@step
def static_single() -> Annotated[str, "static_output_name"]:
    return "null"
```

### Dynamic Naming
Dynamic names can be generated using:

#### Lambda Functions
```python
from random import randint

lambda_namer = lambda: "dynamic_name_" + str(randint(0,42))

@step
def dynamic_single_lambda() -> Annotated[str, lambda_namer]:
    return "null"
```

#### Callable Functions
```python
from random import randint

def func_namer():
    return "dummy_dynamic_" + str(randint(0,42))

@step
def dynamic_single_callable() -> Annotated[str, func_namer]:
    return "null"
```

#### String Templates
Use the following placeholders that ZenML will replace:

* `{date}` will resolve to the current date, e.g. `2024_11_18`
* `{time}` will resolve to the current time, e.g. `11_07_09_326492`

```python
str_namer = "placeholder_name_{date}_{time}"

@step
def dynamic_single_string() -> Annotated[str, str_namer]:
    return "null"
```

### Multiple Output Handling

If you plan to return multiple artifacts from you ZenML step you can flexibly combine all naming options outlined above, like this:

```python
from random import randint

def func_namer():
    return "dummy_dynamic_" + str(randint(0,42))

@step
def mixed_tuple() -> Tuple[
    Annotated[str, "static_output_name"],
    Annotated[str, lambda: "dynamic_name_" + str(randint(0,42))],
    Annotated[str, func_namer],
    Annotated[str, "placeholder_name_{date}_{time}"],
]:
    return "static_namer", "lambda_namer", "func_namer", "str_namer"
```

## Naming in cached runs

If your ZenML step is running with enabled caching and cache was used the names of the outputs artifacts (both static and dynamic) will remain the same as in the original run.

```python
from typing_extensions import Annotated
from typing import Tuple
from random import randint

from zenml import step, pipeline
from zenml.models import PipelineRunResponse


@step
def demo() -> (
    Tuple[
        Annotated[int, lambda: "dummy" + str(randint(0, 42))],
        Annotated[int, "dummy_{date}_{time}"],
    ]
):
    return 42, 43


@pipeline
def my_pipeline():
    demo()


if __name__ == "__main__":
    run_without_cache: PipelineRunResponse = my_pipeline.with_options(
        enable_cache=False
    )()
    run_with_cache: PipelineRunResponse = my_pipeline.with_options(enable_cache=True)()

    assert set(run_without_cache.steps["demo"].outputs.keys()) == set(
        run_with_cache.steps["demo"].outputs.keys()
    )
    print(list(run_without_cache.steps["demo"].outputs.keys()))
```

These 2 runs will produce output like the one below:
```
Initiating a new run for the pipeline: my_pipeline.
Caching is disabled by default for my_pipeline.
Using user: default
Using stack: default
  orchestrator: default
  artifact_store: default
Dashboard URL for Pipeline Run: http://127.0.0.1:8237/runs/e4375452-a72e-45c2-a0df-c59b07089696
Step demo has started.
Step demo has finished in 0.061s.
Pipeline run has finished in 0.100s.

Initiating a new run for the pipeline: my_pipeline.
Using user: default
Using stack: default
  orchestrator: default
  artifact_store: default
Dashboard URL for Pipeline Run: http://127.0.0.1:8237/runs/cb4fffbf-b173-418f-bf4e-11d1bdac377c
Using cached version of step demo.
All steps of the pipeline run were cached.

['dummy_2024_11_19_10_46_52_341267', 'dummy26']
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
