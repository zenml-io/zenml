# Standardizing the Artifacts

Artifacts describe the inputs and outputs of a step in an ML workflow, and they are an integral part of 
any ML pipeline. Due to the wide complexity of ML tasks in general, an artifact can represent a wide 
variety of things, ranging from a trained model to a dataset, or from an evaluation report to a schema.

With ZenML, we aim to improve upon the concept of artifacts by adding abstractions of certain artifact categories, 
which in return helps us and our users with:

- Identifying the inputs and outputs of a step more clearly
- Making it easier to query the metadata store to fetch relevant artifacts
- Implementing auxiliary utility functions on top of the artifact implementation
- Creating an easier interface to interconnect different pipelines

### How does the implementation work?

It is as simple as it gets. All we have to do is to inherit from our `BaseArtifact` implementation and 
give it a unique `TYPE_NAME` as follows:

```python
from zenml.artifacts.base_artifact import BaseArtifact


class DataArtifact(BaseArtifact):
    """Class for all ZenML data artifacts."""

    TYPE_NAME = "DataArtifact"
```

Using this approach, **ZenML** currently supports the following list of categories:
 
- `DataArtifact`
- `ModelArtifact`
- `StatisticsArtifact`
- `SchemaArtifact`

with many more to come in the future.

### How is it being used?

In order to keep our interface as clean and intuitive as possible, we decided to not force our users to use 
these categories when they are creating a step. As they are already using the input and output annotations such as
`pd.DataFrame`, we will take advantage of our materializers to figure our what kind of artifacts you are dealing with.

Let's look at the Pandas Materializer as an example:

```python
class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = [pd.DataFrame]
    ASSOCIATED_ARTIFACT_TYPES = [
        DataArtifact,
        StatisticsArtifact,
        SchemaArtifact,
    ]
```

Here, you see that the `PandasMaterializer` is only associated with `pd.DataFrame`s however it has the option to 
interpret this dataframe either as a `DataArtifact`, a `StatisticsArtifact` or a `SchemaArtifact`. As the `DataArtifact` 
is the first element in the list, it has a priority and unless it is specified otherwise, all the `pd.DataFrame` input
and output annotations will yield a `DataArtifact`.

If you want to see an example on how to go beyond the default behavior, you can also take a look at the following 
example:

```python
@step(output_types={"output_1": SchemaArtifact})
def any_step() -> Output(
    output_1=pd.DataFrame, 
    output_2=pd.DataFrame
):
    ...
    return output_1, output_2
```

Here, we are dealing with a step definition which features two output `pd.DataFrame`s. In the step decorator, we 
explicitly handle `output_1` as a `SchemaArtifact`, whereas the `output_2` will become a `DataArtifact` due to the default 
behavior.

### What's in store for the standard artifacts in the feature?

🚧 This section is WIP.
