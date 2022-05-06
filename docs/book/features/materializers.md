# Materializers

The precise way that data passes between the steps is dictated by `materializers`. The data that flows through steps 
are stored as artifacts and artifacts are stored in artifact stores. The logic that governs the reading and writing of 
data to and from the artifact stores lives in the materializers. In order to control more precisely how data 
flows between steps, one can simply create a custom materializer by sub-classing the `BaseMaterializer` class.

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
this class defines the interface for all materializers. 

Each materializer has an `artifact` object. The most important property of an `artifact` object is the `uri`. The 
`uri` is created by ZenML on pipeline run time and points to the directory of a file system (the artifact store).

The `handle_input` and `handle_return` functions are important. 

- `handle_input` is responsible for **reading** the artifact from the artifact store.
- `handle_return` is responsible for **writing** the artifact to the artifact store.

Each materializer has `ASSOCIATED_TYPES` and `ASSOCIATED_ARTIFACT_TYPES`.

- `ASSOCIATED_TYPES` is the data type that is being stored. ZenML uses this information to call the right materializer 
at the right time. E.g. If a ZenML step returns a `pd.DataFrame`, ZenML will try to find any materializer that has 
`pd.DataFrame` (or its subclasses) in its `ASSOCIATED_TYPES`.
- `ASSOCIATED_ARTIFACT_TYPES` simply define what `type` of artifacts are being stored. This can be `DataArtifact`, 
`StatisticsArtifact`, `DriftArtifact`, etc. This is simply a tag to query certain artifact types in the post-execution 
workflow.
