---
description: Learning how to develop a custom model registry.
---

# Develop a Custom Model Registry

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

{% hint style="warning" %}
**Base abstraction in progress!**

The Model registry stack component is relatively new in ZenML. While it is fully functional, it can be challenging to cover all the ways ML systems deal with model versioning. This means that the API might change in the future. We will keep this page up-to-date with the latest changes.

If you are writing a custom model registry flavor, and you found that the base abstraction is lacking or not flexible enough, please let us know by messaging us on [Slack](https://zenml.io/slack), or by opening an issue on [GitHub](https://github.com/zenml-io/zenml/issues/new/choose)
{% endhint %}

### Base Abstraction

The `BaseModelRegistry` is the abstract base class that needs to be subclassed in order to create a custom component that can be used to register and retrieve models. As model registries can come in many shapes and forms, the base class exposes a deliberately basic and generic interface:

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel, Field, root_validator

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseModelRegistryConfig(StackComponentConfig):
    """Base config for model registries."""


class BaseModelRegistry(StackComponent, ABC):
    """Base class for all ZenML model registries."""

    @property
    def config(self) -> BaseModelRegistryConfig:
        """Returns the config of the model registry."""
        return cast(BaseModelRegistryConfig, self._config)

    # ---------
    # Model Registration Methods
    # ---------

    @abstractmethod
    def register_model(
            self,
            name: str,
            description: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Registers a model in the model registry."""

    @abstractmethod
    def delete_model(
            self,
            name: str,
    ) -> None:
        """Deletes a registered model from the model registry."""

    @abstractmethod
    def update_model(
            self,
            name: str,
            description: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Updates a registered model in the model registry."""

    @abstractmethod
    def get_model(self, name: str) -> RegisteredModel:
        """Gets a registered model from the model registry."""

    @abstractmethod
    def list_models(
            self,
            name: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """Lists all registered models in the model registry."""

    # ---------
    # Model Version Methods
    # ---------

    @abstractmethod
    def register_model_version(
            self,
            name: str,
            description: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
            model_source_uri: Optional[str] = None,
            version: Optional[str] = None,
            description: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
            metadata: Optional[Dict[str, str]] = None,
            zenml_version: Optional[str] = None,
            zenml_run_name: Optional[str] = None,
            zenml_pipeline_name: Optional[str] = None,
            zenml_step_name: Optional[str] = None,
            **kwargs: Any,
    ) -> RegistryModelVersion:
        """Registers a model version in the model registry."""

    @abstractmethod
    def delete_model_version(
            self,
            name: str,
            version: str,
    ) -> None:
        """Deletes a model version from the model registry."""

    @abstractmethod
    def update_model_version(
            self,
            name: str,
            version: str,
            description: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
            stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        """Updates a model version in the model registry."""

    @abstractmethod
    def list_model_versions(
            self,
            name: Optional[str] = None,
            model_source_uri: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
            **kwargs: Any,
    ) -> List[RegistryModelVersion]:
        """Lists all model versions for a registered model."""

    @abstractmethod
    def get_model_version(self, name: str, version: str) -> RegistryModelVersion:
        """Gets a model version for a registered model."""

    @abstractmethod
    def load_model_version(
            self,
            name: str,
            version: str,
            **kwargs: Any,
    ) -> Any:
        """Loads a model version from the model registry."""

    @abstractmethod
    def get_model_uri_artifact_store(
            self,
            model_version: RegistryModelVersion,
    ) -> str:
        """Gets the URI artifact store for a model version."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. To see the full implementation and get the complete docstrings, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/model_registries/base_model_registry.py) .
{% endhint %}

### Build your own custom model registry

If you want to create your own custom flavor for a model registry, you can follow the following steps:

1. Learn more about the core concepts for the model registry [here](./#model-registry-concepts-and-terminology). Your custom model registry will be built on top of these concepts so it helps to be aware of them.
2. Create a class that inherits from `BaseModelRegistry` and implements the abstract methods.
3. Create a `ModelRegistryConfig` class that inherits from `BaseModelRegistryConfig` and adds any additional configuration parameters that you need.
4. Bring the implementation and the configuration together by inheriting from the `BaseModelRegistryFlavor` class. Make sure that you give a `name` to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI with the following command:

```shell
zenml model-registry flavor register <IMAGE-BUILDER-FLAVOR-SOURCE-PATH>
```

{% hint style="warning" %}
It is important to draw attention to how and when these base abstractions are coming into play in a ZenML workflow.

* The **CustomModelRegistryFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomModelRegistryConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Most of all, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are `pydantic` objects under the hood, you can also add your own custom validators here.
* The **CustomModelRegistry** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomModelRegistryFlavor` and the `CustomModelRegistryConfig` are implemented in a different module/path than the actual `CustomModelRegistry`).
{% endhint %}

For a full implementation example, please check out the [MLFlowModelRegistry](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-mlflow.html#zenml.integrations.mlflow)

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
