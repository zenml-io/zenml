---
description: How to pass custom datatypes through steps.
---

# Materializers

A ZenML pipeline is built in a data-centric way. The outputs and inputs of steps
define how steps are connected and the order in which they are executed. Each
step should be considered as its very own process that reads and writes its
inputs and outputs from and to the artifact store. This is where
**Materializers** come into play.

A materializer dictates how a given artifact can be written to and retrieved
from the artifact store and also contains all serialization and deserialization
logic.

Whenever you pass artifacts as outputs from one pipeline step to other steps as
inputs, the corresponding materializer for the respective datatype defines
how this artifact is first serialized and written to the artifact store, and
then deserialized and read in the next step.

For most data types, ZenML already includes built-in materializers that
automatically handle artifacts of those data types. For instance, all of the 
examples from the [Steps and Pipelines](../steps-pipelines/steps-and-pipelines.md)
section were using built-in materializers under the hood to store and load 
artifacts correctly.

However, if you want to pass custom objects between pipeline steps, such as a
PyTorch model that does not inherit from `torch.nn.Module`, then you need to
define a custom Materializer to tell ZenML how to handle this specific data
type.

## Building a Custom Materializer

### Base Implementation

Before we dive into how custom materializers can be built, let us briefly
discuss how a materializers in general is implemented. In the following, you
can see the implementation of the abstract base class `BaseMaterializer`, which
defines the interface of all materializers:

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

### Which Data Type to Handle?

Each materializer has an `ASSOCIATED_TYPES` attribute that contains a list of
data types that this materializer can handle. ZenML uses this information to
call the right materializer at the right time. I.e., if a ZenML step returns a
`pd.DataFrame`, ZenML will try to find any materializer that has `pd.DataFrame`
in its `ASSOCIATED_TYPES`. List the data type of your custom object here to
link the materializer to that data type.

### What Type of Artifact to Generate

Each materializer also has an `ASSOCIATED_ARTIFACT_TYPES` attribute, which
defines what types of artifacts are being stored, such as `DataArtifact`,
`StatisticsArtifact`, `DriftArtifact`, etc. This is not too important for you,
as it is only used as a tag to query certain artifact types in the
[Post Execution Workflow](../steps-pipelines/post-execution-workflow.md).

### Where to Store the Artifact

Each materializer has an `artifact` object. The most important property of an
`artifact` object is the `uri`. The `uri` is automatically created by ZenML
whenever you run a pipeline and points to the directory of a file system where
the artifact is stored (location in the artifact store). This should not be
modified.

### How to Store and Retrieve the Artifact

The `handle_input()` and `handle_return()` methods define the serialization and
deserialization of artifacts.

- `handle_input()` defines how data is read from the artifact store and deserialized,
- `handle_return()` defines hohw data is serialized and saved to the artifact store.

These methods you will need to overwrite according to how you plan to serialize
your objects. E.g., if you have custom PyTorch classes as `ASSOCIATED_TYPES`,
then you might want to use `torch.save()` and `torch.load()` here. For example,
have a look at the materializer in the
[Neural Prophet integration](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/neural_prophet/materializers/neural_prophet_materializer.py).

## Using a Custom Materializer

ZenML automatically scans your source code for definitions of materializers and
registers them for the corresponding data type, so just having a custom
materializer definition in your code is enough to enable the respective data
type to be used in your pipelines.

Alternatively, you can also explicitly define which materializer to use for a
specific step using the `with_return_materializers()` method of the step. E.g.:

```python
first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    ...
).run()
```

When there are multiple outputs, a dictionary of type
`{<OUTPUT_NAME>:<MATERIALIZER_CLASS>}` can be supplied to the
 `with_return_materializers()` method.

{% hint style="info" %} 
Note that `with_return_materializers` only needs to be called for the output of
the first step that produced an artifact of a given data type, all downstream
steps will use the same materializer by default. 
{% endhint %}

### Configuring Materializers at Runtime

As briefly outlined in the
[Runtime Configuration](../steps-pipelines/runtime-configuration.md#defining-materializer-source-codes)
section, which materializer to use for the output of what step can also be
configured within YAML config files.

For each output of your steps, you can define custom materializers to
handle the loading and saving. You can configure them like this in the config:

```yaml
...
steps:
  <STEP_NAME>:
    ...
    materializers:
      <OUTPUT_NAME>:
        name: <MaterializerName>
        file: <relative/filepath>
```

The name of the output can be found in the function declaration, e.g. 
`my_step() -> Output(a: int, b: float)` has `a` and `b` as available output
names.

Similar to other configuration entries, the materializer `name` refers to the 
class name of your materializer, and the `file` should contain a path to the
module where the materializer is defined.

## Basic Example

Let's see how materialization work with a basic example. Let's say you have
a custom class called `MyObject` that flows between two steps in a pipeline:

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
        f"The following object was passed to this step: `{my_obj.name}`"
    )


@pipeline
def first_pipeline(step_1, step_2):
    output_1 = step_1()
    step_2(output_1)


first_pipeline(
    step_1=my_first_step(),
    step_2=my_second_step()
).run()
```

Running the above without a custom materializer will result in the following
error:

`
zenml.exceptions.StepInterfaceError: Unable to find materializer for output 'output' of 
type <class '__main__.MyObj'> in step 'step1'. Please make sure to either explicitly set a materializer for step 
outputs using step.with_return_materializers(...) or registering a default materializer for specific types by 
subclassing BaseMaterializer and setting its ASSOCIATED_TYPES class variable. 
For more information, visit https://docs.zenml.io/guides/common-usecases/custom-materializer.
`

The error message basically says that ZenML does not know how to persist the
object of type `MyObj` (how could it? We just created this!). Therefore, we
have to create our own materializer. To do this, you can extend the
`BaseMaterializer` by sub-classing it, listing `MyObj` in `ASSOCIATED_TYPES`,
and overwriting `handle_input()` and `handle_return()`:

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

{% hint style="info" %}
Pro-tip: Use the ZenML `fileio` module to ensure your materialization logic
works across artifact stores (local and remote like S3 buckets).
{% endhint %}

Now ZenML can use this materializer to handle outputs and inputs of your customs
object. Edit the pipeline as follows to see this in action:

```python
first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()
).run()
```

{% hint style="info" %} Due to the typing of the inputs and outputs and the
ASSOCIATED_TYPES attribute of the materializer, you won't necessarily have to add
`.with_return_materializers(MyMaterializer)` to the step. It should
automatically be detected. It doesn't hurt to be explicit though. {% endhint %}

This will now work as expected and yield the following output:

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

### Code Summary

<details>
    <summary>Code Example for Materializing Custom Objects</summary>

```python
import logging
import os
from typing import Type

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
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'r') as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'w') as f:
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
def first_pipeline(step_1, step_2):
    output_1 = step_1()
    step_2(output_1)


first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()
).run()
```

</details>

## Skipping Materialization

{% hint style="warning" %}
Using artifacts directly might have unintended consequences for downstream
tasks that rely on materialized artifacts. Only skip materialization if there
is no other way to do what you want to do.
{% endhint %}

While materializers should in most cases be used to control how artifacts are 
returned and consumed from pipeline steps, you might sometimes need to have a 
completely non-materialized artifact in a step, e.g., if you need to know the
exact path to your where your artifact is stored.

A non-materialized artifact is a `BaseArtifact` (or any of its subclasses) and
has a property `uri` that points to the unique path in the artifact store where
the artifact is stored. One can use a non-materialized artifact by 
specifying it as the type in the step:

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

### Example

The following shows an example how non-materialized artifacts can be used in
the steps of a pipeline. The pipeline we define will look like this:

```shell
s1 -> s3 
s2 -> s4
```

`s1` and `s2` produce identical artifacts, however `s3` consumes materialized
artifacts while `s4` consumes non-materialized artifacts. `s4` can now use the
`dict_.uri` and `list_.uri` paths directly rather than their materialized
counterparts.

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
    assert isinstance(dict_, dict)
    assert isinstance(list_, list)


@step
def step_4(dict_: DataArtifact, list_: ModelArtifact) -> None:
    assert hasattr(dict_, "uri")
    assert hasattr(list_, "uri")


@pipeline
def example_pipeline(step_1, step_2, sstep_3, step_4):
    step_3(*step_1())
    step_4(*step_2())


example_pipeline(step_1(), step_2(), step_3(), step_4()).run()
```
