---
description: Extend ZenML to implement a custom Artifact Store
---

ZenML comes equipped with [Artifact Store implementations](./overview.md#artifact-store-flavors)
that you can use to store artifacts on a local filesystem or in the managed AWS,
GCP or Azure cloud object storage services. However, if you need to use a
different type of object storage service as a backend for your ZenML Artifact
Store, you can extend ZenML to provide your own custom Artifact Store
implementation.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](../advanced-guide/stacks-components-flavors.md).  
{% endhint %}

## Base Abstraction

The Artifact Store establishes one of the main components in every ZenML stack.
Now, let us take a deeper dive into the fundamentals behind its abstraction,
namely [the `BaseArtifactStore` class](https://apidocs.zenml.io/latest/api_docs/artifact_stores/#zenml.artifact_stores.base_artifact_store.BaseArtifactStore):

1. As it is the base class for a specific type of StackComponent,
    it inherits from the StackComponent class. This sets the `TYPE`
    variable to a StackComponentType. The `FLAVOR` class variable needs to be 
    set in the specific subclass.
2. As ZenML only supports filesystem-based artifact stores, it features an 
    instance configuration parameter called `path`, which will indicate the 
    root path of the artifact store. When creating an instance of any flavor of 
    an `ArtifactStore`, users will have to define this parameter.
3. Moreover, there is an empty class variable called `SUPPORTED_SCHEMES` that 
    needs to be defined in every flavor implementation. It indicates the 
    supported filepath schemes for the corresponding implementation.
    For instance, for the Azure artifact store, this set will be defined as
    `{"abfs://", "az://"}`.
4. Lastly, the base class features a set of `abstractmethod`s: `open`,
   `copyfile`,`exists`,`glob`,`isdir`,`listdir`,`makedirs`,`mkdir`,`remove`,
   `rename`,`rmtree`,`stat`,`walk`. In the implementation of every 
   `ArtifactStore` flavor, it is required to define these methods with respect 
    to the flavor at hand.

Putting all these considerations together, we end up with the following 
implementation:

```python
from zenml.enums import StackComponentType
from zenml.stack import StackComponent

PathType = Union[bytes, str]

class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores."""

    # --- Instance configuration ---
    path: str  # The root path of the artifact store.

    # --- Class variables ---
    TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    # --- User interface ---
    @abstractmethod
    def open(self, name: PathType, mode: str = "r") -> Any:
        """Open a file at the given path."""

    @abstractmethod
    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file from the source to the destination."""

    @abstractmethod
    def exists(self, path: PathType) -> bool:
        """Returns `True` if the given path exists."""

    @abstractmethod
    def glob(self, pattern: PathType) -> List[PathType]:
        """Return the paths that match a glob pattern."""

    @abstractmethod
    def isdir(self, path: PathType) -> bool:
        """Returns whether the given path points to a directory."""

    @abstractmethod
    def listdir(self, path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem."""

    @abstractmethod
    def makedirs(self, path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents."""

    @abstractmethod
    def mkdir(self, path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist."""

    @abstractmethod
    def remove(self, path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation."""

    @abstractmethod
    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file."""

    @abstractmethod
    def rmtree(self, path: PathType) -> None:
        """Deletes dir recursively. Dangerous operation."""

    @abstractmethod
    def stat(self, path: PathType) -> Any:
        """Return the stat descriptor for a given file path."""

    @abstractmethod
    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/latest/api_docs/artifact_stores/#zenml.artifact_stores.base_artifact_store.BaseArtifactStore).
{% endhint %}

#### The effect on the `zenml.io.fileio`

If you created an instance of an artifact store, added it to your stack and 
activated the stack, it will create a filesystem each time you run a ZenML 
pipeline and make it available to the `zenml.io.fileio` module. 

This means that when you utilize a method such as `fileio.open(...)` with a 
filepath which starts with one of the `SUPPORTED_SCHEMES` within 
your steps or materializers, it will be able to use the `open(...)` method 
that you defined within your artifact store.

## Build your own custom artifact store

If you want to implement your own custom Artifact Store, you can 
follow the following steps:

1. Create a class which inherits from [the `BaseArtifactStore` base class](https://apidocs.zenml.io/latest/api_docs/artifact_stores/#zenml.artifact_stores.base_artifact_store.BaseArtifactStore).
2. Define the `FLAVOR` and `SUPPORTED_SCHEMES` class variables.
3. Implement the `abstractmethod`s based on your desired filesystem.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml artifact-store flavor register <THE-SOURCE-PATH-OF-YOUR-ARTIFACT-STORE>
```

ZenML includes a range of Artifact Store implementations, some built-in and
other provided by specific integration modules. You can use them as examples
of how you can extend the [base Artifact Store abstraction](#base-abstraction)
to implement your own custom Artifact Store:

|                                                                                                                                                               | Flavor | Integration |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------------|
| [LocalArtifactStore](https://apidocs.zenml.io/latest/api_docs/artifact_stores/#zenml.artifact_stores.local_artifact_store.LocalArtifactStore)                 | local  | `built-in`  |
| [S3ArtifactStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.s3.artifact_stores.s3_artifact_store.S3ArtifactStore)             | s3     | s3          |
| [GCPArtifactStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.gcp.artifact_stores.gcp_artifact_store.GCPArtifactStore)         | gcp    | gcp         |
| [AzureArtifactStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.azure.artifact_stores.azure_artifact_store.AzureArtifactStore) | azure  | azure       |

