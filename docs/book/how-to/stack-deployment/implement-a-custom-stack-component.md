---
description: How to write a custom stack component flavor
---

# Implement a custom stack component

When building a sophisticated MLOps Platform, you will often need to come up with custom-tailored solutions for your infrastructure or tooling. ZenML is built around the values of composability and reusability which is why the stack component flavors in ZenML are designed to be modular and straightforward to extend.

This guide will help you understand what a flavor is, and how you can develop and use your own custom flavors in ZenML.

## Understanding component flavors

In ZenML, a component type is a broad category that defines the functionality of a stack component. Each type can have multiple flavors, which are specific implementations of the component type. For instance, the type `artifact_store` can have flavors like `local`, `s3`, etc. Each flavor defines a unique implementation of functionality that an artifact store brings to a stack.

## Base Abstractions

Before we get into the topic of creating custom stack component flavors, let us briefly discuss the three core abstractions related to stack components: the `StackComponent`, the `StackComponentConfig`, and the `Flavor`.

### Base Abstraction 1: `StackComponent`

The `StackComponent` is the abstraction that defines the core functionality. As an example, check out the `BaseArtifactStore` definition below: The `BaseArtifactStore` inherits from `StackComponent` and establishes the public interface of all artifact stores. Any artifact store flavor needs to follow the standards set by this base class.

```python
from zenml.stack import StackComponent


class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores."""

    # --- public interface ---

    @abstractmethod
    def open(self, path, mode = "r"):
        """Open a file at the given path."""

    @abstractmethod
    def exists(self, path):
        """Checks if a path exists."""

    ...
```

As each component defines a different interface, make sure to check out the base class definition of the component type that you want to implement and also check out the [documentation on how to extend specific stack components](implement-a-custom-stack-component.md#extending-specific-stack-components).

{% hint style="info" %}
If you would like to automatically track some metadata about your custom stack component with each pipeline run, you can do so by defining some additional methods in your stack component implementation class as shown in the [Tracking Custom Stack Component Metadata](../../how-to/track-metrics-metadata/fetch-metadata-within-steps.md) section.
{% endhint %}

See the full code of the base `StackComponent` class [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/stack\_component.py#L301).

### Base Abstraction 2: `StackComponentConfig`

As the name suggests, the `StackComponentConfig` is used to configure a stack component instance. It is separated from the actual implementation on purpose. This way, ZenML can use this class to validate the configuration of a stack component during its registration/update, without having to import heavy (or even non-installed) dependencies.

{% hint style="info" %}
The `config` and `settings` of a stack component are two separate, yet related entities. The `config` is the static part of your flavor's configuration, defined when you register your flavor. The `settings` are the dynamic part of your flavor's configuration that can be overridden at runtime.

You can read more about the differences [here](../use-configuration-files/runtime-configuration.md).
{% endhint %}

Let us now continue with the base artifact store example from above and take a look at the `BaseArtifactStoreConfig`:

```python
from zenml.stack import StackComponentConfig


class BaseArtifactStoreConfig(StackComponentConfig):
    """Config class for `BaseArtifactStore`."""

    path: str

    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    ...
```

Through the `BaseArtifactStoreConfig`, each artifact store will require users to define a `path` variable. Additionally, the base config requires all artifact store flavors to define a `SUPPORTED_SCHEMES` class variable that ZenML will use to check if the user-provided `path` is actually supported by the flavor.

See the full code of the base `StackComponentConfig` class [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/stack\_component.py#L44).

### Base Abstraction 3: `Flavor`

Finally, the `Flavor` abstraction is responsible for bringing the implementation of a `StackComponent` together with the corresponding `StackComponentConfig` definition and also defines the `name` and `type` of the flavor. As an example, check out the definition of the `local` artifact store flavor below:

```python
from zenml.enums import StackComponentType
from zenml.stack import Flavor


class LocalArtifactStore(BaseArtifactStore):
    ...


class LocalArtifactStoreConfig(BaseArtifactStoreConfig):
    ...


class LocalArtifactStoreFlavor(Flavor):

    @property
    def name(self) -> str:
        """Returns the name of the flavor."""
        return "local"

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type."""
        return StackComponentType.ARTIFACT_STORE

    @property
    def config_class(self) -> Type[LocalArtifactStoreConfig]:
        """Config class of this flavor."""
        return LocalArtifactStoreConfig

    @property
    def implementation_class(self) -> Type[LocalArtifactStore]:
        """Implementation class of this flavor."""
        return LocalArtifactStore
```

See the full code of the base `Flavor` class definition [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/flavor.py#L29).

## Implementing a Custom Stack Component Flavor

Let's recap what we just learned by reimplementing the `S3ArtifactStore` from the `aws` integration as a custom flavor.

We can start with the configuration class: here we need to define the `SUPPORTED_SCHEMES` class variable introduced by the `BaseArtifactStore`. We also define several additional configuration values that users can use to configure how the artifact store will authenticate with AWS:

```python
from zenml.artifact_stores import BaseArtifactStoreConfig
from zenml.utils.secret_utils import SecretField


class MyS3ArtifactStoreConfig(BaseArtifactStoreConfig):
    """Configuration for the S3 Artifact Store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}

    key: Optional[str] = SecretField(default=None)
    secret: Optional[str] = SecretField(default=None)
    token: Optional[str] = SecretField(default=None)
    client_kwargs: Optional[Dict[str, Any]] = None
    config_kwargs: Optional[Dict[str, Any]] = None
    s3_additional_kwargs: Optional[Dict[str, Any]] = None
```

{% hint style="info" %}
You can pass sensitive configuration values as [secrets](../../how-to/interact-with-secrets.md) by defining them as type `SecretField` in the configuration class.
{% endhint %}

With the configuration defined, we can move on to the implementation class, which will use the S3 file system to implement the abstract methods of the `BaseArtifactStore`:

```python
import s3fs

from zenml.artifact_stores import BaseArtifactStore


class MyS3ArtifactStore(BaseArtifactStore):
    """Custom artifact store implementation."""

    _filesystem: Optional[s3fs.S3FileSystem] = None

    @property
    def filesystem(self) -> s3fs.S3FileSystem:
        """Get the underlying S3 file system."""
        if self._filesystem:
            return self._filesystem

        self._filesystem = s3fs.S3FileSystem(
            key=self.config.key,
            secret=self.config.secret,
            token=self.config.token,
            client_kwargs=self.config.client_kwargs,
            config_kwargs=self.config.config_kwargs,
            s3_additional_kwargs=self.config.s3_additional_kwargs,
        )
        return self._filesystem

    def open(self, path, mode: = "r"):
        """Custom logic goes here."""
        return self.filesystem.open(path=path, mode=mode)

    def exists(self, path):
        """Custom logic goes here."""
        return self.filesystem.exists(path=path)
```

{% hint style="info" %}
The configuration values defined in the corresponding configuration class are always available in the implementation class under `self.config`.
{% endhint %}

Finally, let's define a custom flavor that brings these two classes together. Make sure that you give your flavor a globally unique name here.

```python
from zenml.artifact_stores import BaseArtifactStoreFlavor


class MyS3ArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Custom artifact store implementation."""

    @property
    def name(self):
        """The name of the flavor."""
        return 'my_s3_artifact_store'

    @property
    def implementation_class(self):
        """Implementation class for this flavor."""
        from ... import MyS3ArtifactStore

        return MyS3ArtifactStore

    @property
    def config_class(self):
        """Configuration class for this flavor."""
        from ... import MyS3ArtifactStoreConfig

        return MyS3ArtifactStoreConfig
```

{% hint style="info" %}
For flavors that require additional dependencies, you should make sure to define your implementation, config, and flavor classes in separate Python files and to only import the implementation class inside the `implementation_class` property of the flavor class. Otherwise, ZenML will not be able to load and validate your flavor configuration without the dependencies installed.
{% endhint %}

## Managing a Custom Stack Component Flavor

Once you have defined your implementation, config, and flavor classes, you can register your new flavor through the ZenML CLI:

```shell
zenml artifact-store flavor register <path.to.MyS3ArtifactStoreFlavor>
```

{% hint style="info" %}
Make sure to point to the flavor class via dot notation!
{% endhint %}

For example, if your flavor class `MyS3ArtifactStoreFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml artifact-store flavor register flavors.my_flavor.MyS3ArtifactStoreFlavor
```

Afterwards, you should see the new custom artifact store flavor in the list of available artifact store flavors:

```shell
zenml artifact-store flavor list
```

And that's it! You now have a custom stack component flavor that you can use in your stacks just like any other flavor you used before, e.g.:

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=my_s3_artifact_store \
    --path='some-path' \
    ...

zenml stack register <STACK_NAME> \
    --artifact-store <ARTIFACT_STORE_NAME> \
    ...
```

## Tips and best practices

* ZenML resolves the flavor classes by taking the path where you initialized ZenML (via `zenml init`) as the starting point of resolution. Therefore, you and your team should remember to execute `zenml init` in a consistent manner (usually at the root of the repository where the `.git` folder lives). If the `zenml init` command was not executed, the current working directory is used to find implementation classes, which could lead to unexpected behavior.
* You can use the ZenML CLI to find which exact configuration values a specific flavor requires. Check out [this 3-minute video](https://www.youtube.com/watch?v=CQRVSKbBjtQ) for more information.
* You can keep changing the `Config` and `Settings` of your flavor after registration. ZenML will pick up these "live" changes when running pipelines.
* Note that changing the config in a breaking way requires an update of the component (not a flavor). E.g., adding a mandatory name to flavor X field will break a registered component of that flavor. This may lead to a completely broken state where one should delete the component and re-register it.
* Always test your flavor thoroughly before using it in production. Make sure it works as expected and handles errors gracefully.
* Keep your flavor code clean and well-documented. This will make it easier for others to use and contribute to your flavor.
* Follow best practices for the language and libraries you're using. This will help ensure your flavor is efficient, reliable, and easy to maintain.
* We recommend you develop new flavors by using existing flavors as a reference. A good starting point is the flavors defined in the [official ZenML integrations](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations).

## Extending Specific Stack Components

If you would like to learn more about how to build a custom stack component flavor for a specific stack component type, check out the links below:

| **Type of Stack Component**                                                                                                                                  | **Description**                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [Orchestrator](../../component-guide/orchestrators/custom.md)              | Orchestrating the runs of your pipeline                           |
| [Artifact Store](../../component-guide/artifact-stores/custom.md)          | Storage for the artifacts created by your pipelines               |
| [Container Registry](../../component-guide/container-registries/custom.md) | Store for your containers                                         |
| [Step Operator](../../component-guide/step-operators/custom.md)            | Execution of individual steps in specialized runtime environments |
| [Model Deployer](../../component-guide/model-deployers/custom.md)          | Services/platforms responsible for online model serving           |
| [Feature Store](../../component-guide/feature-stores/custom.md)            | Management of your data/features                                  |
| [Experiment Tracker](../../component-guide/experiment-trackers/custom.md)  | Tracking your ML experiments                                      |
| [Alerter](../../component-guide/alerters/custom.md)                        | Sending alerts through specified channels                         |
| [Annotator](../../component-guide/annotators/custom.md)                    | Annotating and labeling data                                      |
| [Data Validator](../../component-guide/data-validators/custom.md)          | Validating and monitoring your data                               |

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
