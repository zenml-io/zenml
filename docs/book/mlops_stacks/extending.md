---
description: How to write a custom stack component flavor?
---

# Extending ZenML

### Runtime configuration

On top of the configuration through the instance parameters, you can also provide an additional runtime configuration to the stack components for your pipeline run. In order to achieve this, you need to provide these configuration parameters as key-value pairs when you run the pipeline:

```python
pipeline.run(runtime_param_1=3, another_param='luna')
```

The provided parameters will be passed to the `prepare_pipeline_deployment` method of each stack component, and you can use this method as an entrypoint to configure your stack components even further.


### Base abstractions

As **stacks** represent the entire configuration of your infrastructure, **stack components** represent the configuration of individual layers within your **stack** which conduct specific self-contained tasks.

Speaking from structural standpoint, these **stack components** are built on top of base abstractions and in their core you will find the `StackComponent` class:

```python
from abc import ABC
from pydantic import BaseModel, Field
from typing import ClassVar
from uuid import UUID, uuid4

from zenml.enums import StackComponentType

class StackComponent(BaseModel, ABC):
    """Abstract class for all components of a ZenML stack."""

    # Instance configuration
    name: str
    uuid: UUID = Field(default_factory=uuid4)

    # Class parameters
    TYPE: ClassVar[StackComponentType]
    FLAVOR: ClassVar[str]

    ...
```

There are a few things to unpack here. Let's talk about Pydantic first. Pydantic is a library for [data validation and settings management](https://pydantic-docs.helpmanual.io/). Using their `BaseModel` is helping us to configure and serialize these components while allowing us to add a validation layer to each stack component instance/implementation.

You can already see how that comes into play here within the base `StackComponent` implementation. As you can see, each instance of a `StackComponent` needs to include a `name` and an auto-generated `uuid`. These variables will be tracked when we serialize the stack component object. (You can exclude an instance configuration parameter from the serialization by giving it a name which starts with `_`.)

Moreover, you can use class variables by denoting them with the `ClassVar[..]`, which are also excluded from the serialization. Each `StackComponent` implementation features two important class variables called the `TYPE` and the `FLAVOR`. The `TYPE` is utilized when we set up the base implementation for a specific type of stack component whereas the `FLAVOR` parameter is used to denote different flavors (which we will cover in the next section).

With these considerations, we can take a look at the `BaseArtifactStore` as an example:

```python
from typing import ClassVar, Set

from zenml.enums import StackComponentType
from zenml.stack import StackComponent


class BaseArtifactStore(StackComponent):
    """Abstract class for all ZenML artifact stores."""

    # Instance configuration
    path: str

    # Class parameters
    TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    ...
```

As you can see, the `BaseArtifactStore` sets the correct `TYPE`, while introducing a new instance variable called `path` and class variable called `SUPPORTED_SCHEMES`, which will be used by all the subclasses of this base implementation.


### Flavors

Now that we have taken a look at the base abstraction of **stack components**, it is time to introduce the concept of **flavors**. In ZenML, a **flavor** represents an implementation of a specific type of **stack component** on top of its base abstraction. As an example, we can take a look at the `LocalArtifactStore`:

```python
from typing import ClassVar, Set

from zenml.artifact_stores import BaseArtifactStore


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    # Class configuration
    FLAVOR: ClassVar[str] = "local"
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    ...
```

As you can see from the example above, the `LocalArtifactStore` inherits from the corresponding base abstraction `BaseArtifactStore` and implements a local version. While creating this class, it is critical to set the `FLAVOR` class variable, as we will use it as a reference when we create an instance of this stack component.

Through the base abstractions, ZenML also enables you to create your own flavors for any type of stack component. In order to achieve this, you can use the corresponding base abstraction, create your own implementation, and register it through the CLI:

```python
from typing import ClassVar, Set

from zenml.artifact_stores import BaseArtifactStore


class MyCustomArtifactStore(BaseArtifactStore):
    """Custom artifact store implementation."""

    # Class configuration
    FLAVOR: ClassVar[str] = "custom"
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"custom://"}

    ...
```

followed by:

```shell
zenml artifact-store flavor register path.to.MyCustomArtifacStore
```

Once you register your new flavor, you can see it in the CLI with:

```shell
zenml artifact-store flavor list
```