---
description: Control how data is persisted between steps.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


A ZenML pipeline is built in a data-centric way. The outputs and inputs of steps
define how steps are connected and the order in which they are executed. Each
step should be considered as its very own process that reads and writes its
inputs and outputs from and to the artifact store. This is where
**materializers** come into play.

# Materializers: Serializing and deserializing your artifacts

A materializer dictates how a given artifact can be written to and retrieved
from the artifact store. It contains all serialization and deserialization
logic.

## What is a materializer?

```python
from typing import Type, Any
from zenml.materializers.base_materializer import BaseMaterializerMeta


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPES = ()
    ASSOCIATED_TYPES = ()

    def __init__(self, artifact: "BaseArtifact"):
        """Initializes a materializer with the given artifact."""
        self.artifact = artifact

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Write logic here to handle input of the step function.

        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.
        """
        # read from self.artifact.uri
        ...

    def handle_return(self, data: Any) -> None:
        """Write logic here to handle return of the step function.

        Args:
            data: Any object that is specified as an input artifact of the step.
        """
        # write `data` to self.artifact.uri
        ...
```

Above you can see the basic definition of the `BaseMaterializer`. All other
materializers inherit from this class, and this class defines the interface of
all materializers.

Each materializer has an `artifact` object. The most important property of an
`artifact` object is the `uri`. The `uri` is created by ZenML at pipeline run
time and points to the directory of a file system (the artifact store).

The `handle_input` and `handle_return` functions are important.

- `handle_input` is responsible for **reading** the artifact from the artifact
  store.
- `handle_return` is responsible for **writing** the artifact to the artifact
  store.

Each materializer has `ASSOCIATED_TYPES` and `ASSOCIATED_ARTIFACT_TYPES`.

- `ASSOCIATED_TYPES` is the data type that is being stored. ZenML uses this
  information to call the right materializer at the right time. i.e. If a ZenML
  step returns a `pd.DataFrame`, ZenML will try to find any materializer that
  has `pd.DataFrame` (or its subclasses) in its `ASSOCIATED_TYPES`.
- `ASSOCIATED_ARTIFACT_TYPES` simply define what `type` of artifacts are being
  stored. This can be `DataArtifact`, `StatisticsArtifact`, `DriftArtifact`,
  etc. This is simply a tag to query certain artifact types in the
  post-execution workflow.

## Writing a custom materializer

Let's say you have a custom class called `MyObject` that flows between two steps
in a pipeline:

```python
import logging
from zenml.steps import step
from zenml.pipelines import pipeline


class MyObj:
    def __init__(self, name: str):
        self.name = name


@step
def my_first_step() -> MyObj:
    """Step that returns an object of type MyObj"""
    return MyObj("my_object")


@step
def my_second_step(my_obj: MyObj) -> None:
    """Step that logs the input object and returns nothing."""
    logging.info(
        f"The following object was passed to this step: `{my_obj.name}`")


@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1 = step_1()
    step_2(output_1)


first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()
```

Running the above without a custom materializer will result in the following
error:

```shell
zenml.exceptions.StepInterfaceError: Unable to find materializer for output 'output' of 
type `<class '__main__.MyObj'>` in step 'step1'. Please make sure to either explicitly set a materializer for step 
outputs using `step.with_return_materializers(...)` or registering a default materializer for specific types by 
subclassing `BaseMaterializer` and setting its `ASSOCIATED_TYPES` class variable. 
For more information, visit https://docs.zenml.io/guides/common-usecases/custom-materializer.
```

The above basically means that ZenML does not know how to persist the object of
type `MyObj` between steps (how could it? We just created this!). Therefore, we
have to create our own materializer. To do this you can simply extend the
`BaseMaterializer` by sub-classing it.

```python
import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyObj,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[MyObj]) -> MyObj:
        """Read from artifact store"""
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'r') as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'w') as f:
            f.write(my_obj.name)
```

Pro-tip: Use the ZenML `fileio` module to ensure your materialization logic
works across artifact stores (local and remote like S3 buckets).

Now ZenML can use this materializer to handle outputs and inputs of your customs
object. Edit the pipeline as follows to see this in action:

```python
first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()).run()
```

{% hint style="info" %} Due to the typing of the in- and outputs and the
ASSOCIATED_TYPES attribute of the materializer you won't necessarily have to add
`.with_return_materializers(MyMaterializer)` to the step. It should
automatically be detected. It doesn't hurt to be explicit though. {% endhint %}

For multiple outputs a dictionary can be supplied of type `{OUTPUT_NAME:
MATERIALIZER_CLASS}` to the `with_return_materializers` function.

Also, notice that `with_return_materializers` is only called on `step1`, all
downstream steps will use the same materializer by default.

This will yield the proper response as follows:

```shell
Creating run for pipeline: `first_pipeline`
Cache enabled for pipeline `first_pipeline`
Using stack `default` to run pipeline `first_pipeline`...
Step `my_first_step` has started.
Step `my_first_step` has finished in 0.081s.
Step `my_second_step` has started.
The following object was passed to this step: `my_object`
Step `my_second_step` has finished in 0.048s.
Pipeline run `first_pipeline-22_Apr_22-10_58_51_135729` has finished in 0.153s.
```

### Summary in Code

<details>
    <summary>Code Example of this Section</summary>

```python
import os
from typing import Type
import logging

from zenml.steps import step
from zenml.pipelines import pipeline

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class MyObj:
    def __init__(self, name: str):
        self.name = name


class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyObj,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[MyObj]) -> MyObj:
        """Read from artifact store"""
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'r') as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'w') as f:
            f.write(my_obj.name)


@step
def my_first_step() -> MyObj:
    """Step that returns an object of type MyObj"""
    return MyObj("my_object")


@step
def my_second_step(my_obj: MyObj) -> None:
    """Step that log the input object and returns nothing."""
    logging.info(
        f"The following object was passed to this step: `{my_obj.name}`")


@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1 = step_1()
    step_2(output_1)


first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()).run()
```

</details>

## Skip materialization

While in most cases, [materializers](../developer-guide/materializer.md)
should be used to control how artifacts are consumed and output from steps in a
pipeline, you will sometimes need to have a completely non-materialized artifact
in a step.

A non-materialized artifact is a `BaseArtifact` (or any of its subclasses) and
has a property `uri` that points to the unique path in the [artifact store](../core-concepts.md) where the artifact is stored. One
can use a non-materialized artifact by simply specifying it as the type in the
step:

```python
from zenml.artifacts import DataArtifact
from zenml.steps import step


@step
def my_step(my_artifact: DataArtifact)  # rather than pd.DataFrame
    pass
```

The list of raw artifact types can be found in `zenml.artifacts.*` and include
`ModelArtifact`, `DataArtifact` etc. Materializers link pythonic types to these
artifact types implicitly, e.g., a `keras.model` or `torch.nn.Module` are
pythonic types that are both linked to `ModelArtifact` implicitly via their
materializers. When using artifacts directly, one must be aware of which type
they are by looking at the previous step's materializer: if the previous step
produces a `ModelArtifact` then you should specify `ModelArtifact` in a
non-materialized step.

Be careful: Using artifacts directly like this might have unintended
consequences for downstream tasks that rely on materialized artifacts.

### A simple example

A simple example can suffice to showcase how to use non-materialized artifacts:

```python
from typing import Dict, List
from zenml.artifacts import DataArtifact, ModelArtifact
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

`s1` and `s2` produce identical artifacts, however `s3` consumes materialized
artifacts while `s4` consumes non-materialized artifacts. `s4` can now use the
`dict_.uri` and `list_.uri` paths directly rather than their materialized
counterparts.
