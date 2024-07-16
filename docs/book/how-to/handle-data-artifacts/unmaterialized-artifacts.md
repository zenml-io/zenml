---
description: Skip materialization of artifacts.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Unmaterialized artifacts

A ZenML pipeline is built in a data-centric way. The outputs and inputs of steps define how steps are connected and the order in which they are executed. Each step should be considered as its very own process that reads and writes its inputs and outputs from and to the [artifact store](../../component-guide/artifact-stores/artifact-stores.md). This is where **materializers** come into play.

A materializer dictates how a given artifact can be written to and retrieved from the artifact store and also contains all serialization and deserialization logic. Whenever you pass artifacts as outputs from one pipeline step to other steps as inputs, the corresponding materializer for the respective data type defines how this artifact is first serialized and written to the artifact store, and then deserialized and read in the next step. Read more about this [here](handle-custom-data-types.md).

However, there are instances where you might **not** want to materialize an artifact in a step, but rather use a reference to it instead.
This is where skipping materialization comes in.

{% hint style="warning" %}
Skipping materialization might have unintended consequences for downstream tasks that rely on materialized artifacts. Only skip materialization if there is no other way to do what you want to do.
{% endhint %}

## How to skip materialization

While materializers should in most cases be used to control how artifacts are returned and consumed from pipeline steps, you might sometimes need to have a completely unmaterialized artifact in a step, e.g., if you need to know the exact path to where your artifact is stored.

An unmaterialized artifact is a [`zenml.materializers.UnmaterializedArtifact`](https://sdkdocs.zenml.io/latest/core_code_docs/core-artifacts/#zenml.artifacts.unmaterialized_artifact). Among others, it has a property `uri` that points to the unique path in the artifact store where the artifact is persisted. One can use an unmaterialized artifact by specifying `UnmaterializedArtifact` as the type in the step:

```python
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml import step

@step
def my_step(my_artifact: UnmaterializedArtifact):  # rather than pd.DataFrame
    pass
```

## Code Example

The following shows an example of how unmaterialized artifacts can be used in the steps of a pipeline. The pipeline we define will look like this:

```shell
s1 -> s3 
s2 -> s4
```

`s1` and `s2` produce identical artifacts, however `s3` consumes materialized artifacts while `s4` consumes unmaterialized artifacts. `s4` can now use the `dict_.uri` and `list_.uri` paths directly rather than their materialized counterparts.

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Dict, List, Tuple

from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml import pipeline, step


@step
def step_1() -> Tuple[
    Annotated[Dict[str, str], "dict_"],
    Annotated[List[str], "list_"],
]:
    return {"some": "data"}, []


@step
def step_2() -> Tuple[
    Annotated[Dict[str, str], "dict_"],
    Annotated[List[str], "list_"],
]:
    return {"some": "data"}, []


@step
def step_3(dict_: Dict, list_: List) -> None:
    assert isinstance(dict_, dict)
    assert isinstance(list_, list)


@step
def step_4(
        dict_: UnmaterializedArtifact,
        list_: UnmaterializedArtifact,
) -> None:
    print(dict_.uri)
    print(list_.uri)


@pipeline
def example_pipeline():
    step_3(*step_1())
    step_4(*step_2())


example_pipeline()
```

You can see another example of using an `UnmaterializedArtifact` when triggering a [pipeline from another](../trigger-pipelines/trigger-a-pipeline-from-another.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
