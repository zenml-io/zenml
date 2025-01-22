---
description: Learning how to develop a custom model deployer.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Develop a Custom Model Deployer

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

To deploy and manage your trained machine-learning models, ZenML provides a stack component called `Model Deployer`. This component is responsible for interacting with the deployment tool, framework, or platform.

When present in a stack, the model deployer can also act as a registry for models that are served with ZenML. You can use the model deployer to list all models that are currently deployed for online inference or filtered according to a particular pipeline run or step, or to suspend, resume or delete an external model server managed through ZenML.

### Base Abstraction

In ZenML, the base abstraction of the model deployer is built on top of three major criteria:

1. It needs to ensure efficient deployment and management of models in accordance with the specific requirements of the serving infrastructure, by holding all the stack-related configuration attributes required to interact with the remote model serving tool, service, or platform.
2. It needs to implement the continuous deployment logic necessary to deploy models in a way that updates an existing model server that is already serving a previous version of the same model instead of creating a new model server for every new model version (see the `deploy_model` abstract method). This functionality can be consumed directly from ZenML pipeline steps, but it can also be used outside the pipeline to deploy ad-hoc models. It is also usually coupled with a standard model deployer step, implemented by each integration, that hides the details of the deployment process from the user.
3. It needs to act as a ZenML BaseService registry, where every BaseService instance is used as an internal representation of a remote model server (see the `find_model_server` abstract method). To achieve this, it must be able to re-create the configuration of a BaseService from information that is persisted externally, alongside, or even as part of the remote model server configuration itself. For example, for model servers that are implemented as Kubernetes resources, the BaseService instances can be serialized and saved as Kubernetes resource annotations. This allows the model deployer to keep track of all externally running model servers and to re-create their corresponding BaseService instance representations at any given time. The model deployer also defines methods that implement basic life-cycle management on remote model servers outside the coverage of a pipeline (see `stop_model_server` , `start_model_server` and `delete_model_server`).

Putting all these considerations together, we end up with the following interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type
from uuid import UUID

from zenml.enums import StackComponentType
from zenml.services import BaseService, ServiceConfig
from zenml.stack import StackComponent, StackComponentConfig, Flavor

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BaseModelDeployerConfig(StackComponentConfig):
    """Base class for all ZenML model deployer configurations."""


class BaseModelDeployer(StackComponent, ABC):
    """Base class for all ZenML model deployers."""

    @abstractmethod
    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Abstract method to deploy a model."""

    @staticmethod
    @abstractmethod
    def get_model_server_info(
            service: BaseService,
    ) -> Dict[str, Optional[str]]:
        """Give implementation-specific way to extract relevant model server
        properties for the user."""

    @abstractmethod
    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Abstract method to stop a model server."""

    @abstractmethod
    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Abstract method to start a model server."""

    @abstractmethod
    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to delete a model server."""


class BaseModelDeployerFlavor(Flavor):
    """Base class for model deployer flavors."""

    @property
    @abstractmethod
    def name(self):
        """Returns the name of the flavor."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.MODEL_DEPLOYER

    @property
    def config_class(self) -> Type[BaseModelDeployerConfig]:
        """Returns `BaseModelDeployerConfig` config class.

        Returns:
                The config class.
        """
        return BaseModelDeployerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseModelDeployer]:
        """The class that implements the model deployer."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see the full implementation and get the complete docstrings, please check the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-model\_deployers/#zenml.model\_deployers.base\_model\_deployer.BaseModelDeployer) .
{% endhint %}

### Building your own model deployers

If you want to create your own custom flavor for a model deployer, you can follow the following steps:

1. Create a class that inherits from the `BaseModelDeployer` class and implements the abstract methods.
2. If you need to provide any configuration, create a class that inherits from the `BaseModelDeployerConfig` class and add your configuration parameters.
3. Bring both the implementation and the configuration together by inheriting from the `BaseModelDeployerFlavor` class. Make sure that you give a `name` to the flavor through its abstract property.
4. Create a service class that inherits from the `BaseService` class and implements the abstract methods. This class will be used to represent the deployed model server in ZenML.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml model-deployer flavor register <path.to.MyModelDeployerFlavor>
```

For example, if your flavor class `MyModelDeployerFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml model-deployer flavor register flavors.my_flavor.MyModelDeployerFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](../../how-to/setting-up-a-project-repository/best-practices.md) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml model-deployer flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomModelDeployerFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomModelDeployerConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomModelDeployer** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomModelDeployerFlavor` and the `CustomModelDeployerConfig` are implemented in a different module/path than the actual `CustomModelDeployer`).
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
