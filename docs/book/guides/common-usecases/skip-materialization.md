---
description: Skip materialization when needed.
---

# Skip materialization

While in most cases, [materializers](custom-materializer.md) should be used to control 
how artifacts are consumed and output from steps in a pipeline, there is some times a 
need to have a completely non-materialized artifact in a step.

A non-materialized artifact is `BaseArtifact` (or any of its subclasses) and has a propertly `uri` that points 
to the unique path in the [artifact store](../../introduction/core-concepts.md) where the 
artifact is supposed to be stored. One can use a non-materialized artifact by simply specifying it as the type in the step:

```python
@step
def my_step(my_artifact: DataArtifact)  # rather than pd.DataFrame
    pass
```

The list of raw artifact types can be found in `zenml.artifacts.*` and include `ModelArtifact`, `DataArtifact` etc. 
Materializers link pythonic types to these artifact types implicitly, e.g., a `keras.model` or `torch.nn.Module` are pythonic 
types that are both linked to `ModelArtifact` implicitly via their materializers. When using artifacts directly, one must 
be aware of which type they are by looking at the previous steps materializer, i.e., if the previous step produces a 
`ModelArtifact` then you should specify `ModelArtifact` in a non-materialized step.

Be careful: Using artifacts directly like this might have unintended consequences to downstream 
tasks that rely on materialized artifacts.

## A simple example

A simple examples show-casing how to use non-materialized artifacts:

```python
from typing import Dict, List
from zenml.artifacts import DataArtifact
from zenml.pipelines import pipeline
from zenml.steps import Output, step

@step
def step_1() -> Output(dict_=Dict, list_=List):
    return {"some": "data"}, []

@step
def step_2() -> Output(dict_=Dict, list_=List):
    return {"some": "data"}, []

@step
def step_3(dict_: Dict, list_: List) -> None:
    assert type(dict_) is dict
    assert type(list_) is list

@step
def step_4(dict_: DataArtifact, list_: ModelArtifact) -> None:
    assert hasattr(dict_, "uri")
    assert hasattr(list_, "uri")

@pipeline
def p(s1, s2, s3, s4):
    s3(*s1())
    s4(*s2())

p(step_1(), step_2(), step_3(), step_4()).run()
```

In the above the pipeline looks as follows:

```shell
s1 -> s3 
s2 -> s4
```

`s1` and `s2` produce identical artifacts, however, `s3` consumes materialized artifacts 
while `s4` consumes non-materialized artifacts. `s4` will can now use the `dict_.uri` 
and `list_.uri` paths directly rather than their materialized counterparts.