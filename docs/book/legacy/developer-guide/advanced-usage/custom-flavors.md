---
description: How to write a custom stack component flavor
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


When building sophisticated ML workflows, you will often need to come up with
custom-tailed solutions. Sometimes, this might even require you to use custom 
components for your infrastructure or tooling.

That is exactly why the stack components in ZenML were designed to be
modular and straightforward to extend. Using ZenML's base abstractions, you can
create your own stack component flavors and use custom solutions for any stack
component.

## Base Abstractions

Before we get into how custom stack component flavors can be defined, let us
briefly discuss how ZenML's abstraction for stack components are designed.

### Abstract Stack Component Base Abstraction

All stack components in ZenML inherit from a common abstract base class 
`StackComponent`, parts of which you can see below:

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

### Component-Specific Base Abstraction

For each stack component, there then exists another component-specific base
abstraction which all flavors should inherit from. These component-specific
are themselves subclasses of `StackComponent`.

As an example, let us take a look at the `BaseArtifactStore`:

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

## Building Custom Stack Component Flavors

In order to build a new flavor for a stack component, you need to create a
custom class that inherits from the respective component-specific base 
abstraction, defines the `FLAVOR` class variable, and implements any
abstract or flavor-specific methods and properties. 

As an example, this is how you could define a custom artifact store:

```python
from typing import ClassVar, Set

from zenml.artifact_stores import BaseArtifactStore


class MyCustomArtifactStore(BaseArtifactStore):
    """Custom artifact store implementation."""

    # Class configuration
    FLAVOR: ClassVar[str] = "custom"  # the name you want your flavor to have
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"custom://"}  # implement this

    ...  # custom functionality
```

As you can see from the example above, `MyCustomArtifactStore` inherits from the corresponding base abstraction `BaseArtifactStore` and implements a `custom` flavor. 

You could now register this `custom` artifact store via 
`zenml artifact-store flavor register`:

```shell
zenml artifact-store flavor register <path.to.MyCustomArtifacStore>
```

Afterwards, you should see the new `custom` artifact store in the list of
available artifact store flavors:

```shell
zenml artifact-store flavor list
```

And that's it, you now have defined a custom stack component flavor that you
can use in any of your stacks just like any other flavor you used before, e.g.:

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=custom \
    ...

zenml stack register <STACK_NAME> \
    --artifact-store <ARTIFACT_STORE_NAME> \
    ...
```

{% hint style="info" %}
If your custom stack component flavor requires special setup before it can be
used, check out the [Managing Stack Component States](./stack-state-management.md)
section for more details.
{% endhint %}

## Extending Specific Stack Components

If you would like to learn more about how to build a custom stack component
flavor for a specific stack component, please check the links below:

| **Type of Stack Component**                 | **Description**                                                                               |
|---------------------------------------------|-----------------------------------------------------------------------------------------------|
| [Orchestrator](../../mlops-stacks/orchestrators/custom.md)              | Orchestrating the runs of your pipeline                           |
| [Artifact Store](../../mlops-stacks/artifact-stores/custom.md)          | Storage for the artifacts created by your pipelines               |
| [Metadata Store](../../mlops-stacks/metadata-stores/custom.md)          | Tracking the execution of your pipelines/steps                    |
| [Container Registry](../../mlops-stacks/container-registries/custom.md) | Store for your containers                                         |
| [Secrets Manager](../../mlops-stacks/secrets-managers/custom.md)        | Centralized location for the storage of your secrets              |
| [Step Operator](../../mlops-stacks/step-operators/custom.md)            | Execution of individual steps in specialized runtime environments |
| [Model Deployer](../../mlops-stacks/model-deployers/custom.md)          | Services/platforms responsible for online model serving           |
| [Feature Store](../../mlops-stacks/feature-stores/custom.md)            | Management of your data/features                                  |
| [Experiment Tracker](../../mlops-stacks/experiment-trackers/custom.md)  | Tracking your ML experiments                                      |
| [Alerter](../../mlops-stacks/alerters/custom.md)                        | Sending alerts through specified channels                         |
