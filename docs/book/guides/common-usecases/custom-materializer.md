---
description: All code in this guide can be found [here](https://github.com/zenml-io/zenml/tree/main/examples/custom_materializer).
---

# Creating a custom materializer

## What is a materializer?

The precise way that data passes between the steps is dictated by materializers. The data that flows through steps 
are stored as artifacts and artifacts are stored in artifact stores. The logic that governs the reading and writing of 
data to and from the artifact stores lives in the materializers.

```python
class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPES = []
    ASSOCIATED_TYPES = []

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

Above you can see the basic definition of the `BaseMaterializer`. All other materializers inherit from this class, and 
this class defines the interface of all materializers. 

Each materializer has an `artifact` object. The most important property of an `artifact` object is the `uri`. The 
`uri` is created by ZenML at pipeline run time and points to the directory of a file system (the artifact store).

The `handle_input` and `handle_return` functions are important. 

- `handle_input` is responsible for **reading** the artifact from the artifact store.
- `handle_return` is responsible for **writing** the artifact to the artifact store.

Each materializer has `ASSOCIATED_TYPES` and `ASSOCIATED_ARTIFACT_TYPES`.

- `ASSOCIATED_TYPES` is the data type that is being stored. ZenML uses this information to call the right materializer 
at the right time. i.e. If a ZenML step returns a `pd.DataFrame`, ZenML will try to find any materializer that has 
`pd.DataFrame` (or its subclasses) in its `ASSOCIATED_TYPES`.
- `ASSOCIATED_ARTIFACT_TYPES` simply define what `type` of artifacts are being stored. This can be `DataArtifact`, 
`StatisticsArtifact`, `DriftArtifact`, etc. This is simply a tag to query certain artifact types in the post-execution 
workflow.

## Extending the `BaseMaterializer`

In order to control more precisely how data flowing between steps is treated, one can simply extend the 
`BaseMaterializer` by sub-classing it.

```python
class MyCustomMaterializer(BaseMaterializer):
    """Define my own materialization logic"""
    ASSOCIATED_ARTIFACT_TYPES = [...]
    ASSOCIATED_TYPES = [...]


    def handle_input(self, data_type: Type[Any]) -> Any:
        # read from self.artifact.uri
        ...

    def handle_return(self, data: Any) -> None:
        # write `data` to self.artifact.uri
        ...
```

For example, let's say you a custom object called `MyObject` that flows between two steps in a pipeline:

```python
from zenml.steps import step
from zenml.pipelines import pipeline


class MyObj:
    def __init__(self, name: str):
        self.name = name

@step
def step1() -> MyObj:
    return MyObj("jk")

@step
def step1(my_obj: MyObj):
    print(my_obj)

@pipeline
def pipe(step1, step2):
    step2(step1())

pipe(
    step1=step1(), 
    step2=step2()
).run()
```

Running the above without a custom materializer will result in the following error:

```shell
zenml.exceptions.StepInterfaceError: Unable to find materializer for output 'output' of 
type `<class '__main__.MyObj'>` in step 'step1'. Please make sure to either explicitly set a materializer for step 
outputs using `step.with_return_materializers(...)` or registering a default materializer for specific types by 
subclassing `BaseMaterializer` and setting its `ASSOCIATED_TYPES` class variable. 
For more information, visit https://docs.zenml.io/guides/common-usecases/custom-materializer.
```

The above basically means that ZenML does not know how to persist the object of type `MyObj` between steps (how could 
it? We just created this!). Therefore, we can create our own materializer:

```python
import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = [MyObj]
    ASSOCIATED_ARTIFACT_TYPES = [DataArtifact]

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

Pro-tip: Use the ZenML `fileio` handle to ensure your materialization logic works across artifact stores (local and 
remote like S3 buckets).

Then edit the pipeline as follows:

```python
pipe(
    step1=step1().with_return_materializers(MyMaterializer),
    step2=step2()
).run()
```

Please note that for multiple outputs a dictionary can be supplied of type `{OUTPUT_NAME: MATERIALIZER_CLASS}` to the 
`with_return_materializers` function.

Also, notice that `with_return_materializers` need only be called on step1, all downstream steps will use the same 
materializer by default.

This will yield the proper response as follows:

```shell
Creating run for pipeline: `pipe`
Cache enabled for pipeline `pipe`
Using stack `local_stack` to run pipeline `pipe`...
Step `step1` has started.
Step `step1` has finished in 0.035s.
Step `step2` has started.
jk
Step `step2` has finished in 0.036s.
Pipeline run `pipe-24_Jan_22-23_12_18_504593` has finished in 0.080s.
```