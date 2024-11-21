---
description: Understand how you can name your ZenML artifacts.
---

# How Artifact Naming works in ZenML 

In ZenML pipelines, you often need to reuse the same step multiple times with different inputs, resulting in multiple artifacts. However, the default naming convention for artifacts can make it challenging to track and differentiate between these outputs, especially when they need to be used in subsequent pipelines. Below you can find a detailed exploration of how you might name your output artifacts dynamically or statically, depending on your needs.

ZenML uses type annotations in function definitions to determine artifact names. Output artifacts with the same name are saved with incremented version numbers.

ZenML provides flexible options for naming output artifacts, supporting both static and dynamic naming strategies:
- Names can be generated dynamically at runtime
- Support for string templates (standard and custom placeholders supported)
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

#### String Templates Using Standard Placeholders
Use the following placeholders that ZenML will replace automatically:

* `{date}` will resolve to the current date, e.g. `2024_11_18`
* `{time}` will resolve to the current time, e.g. `11_07_09_326492`

```python
str_namer = "placeholder_name_{date}_{time}"

@step
def dynamic_single_string() -> Annotated[str, str_namer]:
    return "null"
```

#### String Templates Using Custom Placeholders
Use any placeholders that ZenML will replace for you, if they are provided into a step via `extra_name_placeholders` parameter:

```python
str_namer = "placeholder_name_{custom_placeholder}_{time}"

@step(extra_name_placeholders={"custom_placeholder": "some_substitute"})
def dynamic_single_string() -> Annotated[str, str_namer]:
    return "null"
```

Another option is to use `with_options` to dynamically redefine the placeholder, like this:

```python
str_namer = "{stage}_dataset"

@step
def extract_data(source: str) -> Annotated[str, str_namer]:
    ...
    return "my data"

@pipeline
def extraction_pipeline():
    extract_data.with_options(extra_name_placeholders={"stage": "train"})(source="s3://train")
    extract_data.with_options(extra_name_placeholders={"stage": "test"})(source="s3://test")
```

### Multiple Output Handling

If you plan to return multiple artifacts from you ZenML step you can flexibly combine all naming options outlined above, like this:

```python
@step
def mixed_tuple() -> Tuple[
    Annotated[str, "static_output_name"],
    Annotated[str, "placeholder_name_{date}_{time}"],
]:
    return "static_namer", "str_namer"
```

## Naming in cached runs

If your ZenML step is running with enabled caching and cache was used the names of the outputs artifacts (both static and dynamic) will remain the same as in the original run.

```python
from typing_extensions import Annotated
from typing import Tuple

from zenml import step, pipeline
from zenml.models import PipelineRunResponse


@step(extra_name_placeholders={"custom_placeholder": "resolution"})
def demo() -> Tuple[
    Annotated[int, "dummy_{date}_{time}"],
    Annotated[int, "dummy_{custom_placeholder}"],
]:
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
You can visualize your pipeline runs in the ZenML Dashboard. In order to try it locally, please run zenml login --local.
Step demo has started.
Step demo has finished in 0.038s.
Pipeline run has finished in 0.064s.
Initiating a new run for the pipeline: my_pipeline.
Using user: default
Using stack: default
  orchestrator: default
  artifact_store: default
You can visualize your pipeline runs in the ZenML Dashboard. In order to try it locally, please run zenml login --local.
Using cached version of step demo.
All steps of the pipeline run were cached.
['dummy_2024_11_21_14_27_33_750134', 'dummy_resolution']
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
