---
description: How to integrate your own Model Registry flavor
---

{% hint style="warning" %}
**Base abstraction in progress!**

The Model registry stack component is relatively new in ZenML, While it is fully
functional, it can be challenging to cover how every possible ML system deals with
model versioning. This means that the API might change in the future. We will 
keep this page up to date with the latest changes.

If you are writing a custom Model Registry flavor, and you found that the base
abstraction is lacking or not flexible enough, please let us know by talking to
us on [Slack](https://zenml.io/slack) or by opening an issue on
[GitHub](https://github.com/zenml-io/zenml/issues/new/choose)
{% endhint %}

## Base Abstraction

The `BaseModelRegistry` is the abstract base class that needs to be subclassed
in order to create a custom component that can be used to register and retrieve
models. As model registries can come in many shapes and forms, the base class
exposes a deliberately basic and generic interface:

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
        """Returns the config of the model registries."""
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
    ) -> ModelRegistration:
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
    ) -> ModelRegistration:
        """Updates a registered model in the model registry."""

    @abstractmethod
    def get_model(self, name: str) -> ModelRegistration:
        """Gets a registered model from the model registry."""

    @abstractmethod
    def list_models(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[ModelRegistration]:
        """Lists all registered models in the model registry."""

    @abstractmethod
    def check_model_exists(self, name: str) -> bool:
        """Checks if a model exists in the model registry."""

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
        version_description: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        registry_metadata: Optional[Dict[str, str]] = None,
        zenml_version: Optional[str] = None,
        zenml_pipeline_run_id: Optional[str] = None,
        zenml_pipeline_name: Optional[str] = None,
        zenml_step_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelVersion:
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
        version_description: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        version_stage: Optional[ModelVersionStage] = None,
    ) -> ModelVersion:
        """Updates a model version in the model registry."""

    @abstractmethod
    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[ModelVersion]:
        """Lists all model versions for a registered model."""

    @abstractmethod
    def get_model_version(self, name: str, version: str) -> ModelVersion:
        """Gets a model version for a registered model."""

    @abstractmethod
    def check_model_version_exists(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Checks if a model version exists in the model registry."""

    @abstractmethod
    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Loads a model version from the model registry."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check
[the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/model_registries/base_model_registry.py).
{% endhint %}

## Build your own custom Model Registry

If you want to create your own custom flavor for an image builder, you can 
follow the following steps:

1. Read About the Concept and Terminology of the Model Registry 
   [here](model-registries.md#model-registry-concepts-and-terminology) and 
   define the scope of your custom model registry and how it can leverage the
   theses concepts.
2. Create a class that inherits from `BaseModelRegistry` and implement the 
   abstract methods. 
3. Create a `ModelRegistryConfig` class that inherits from 
   `BaseModelRegistryConfig` and add any additional configuration parameters 
   that you need.
4. Bring both of the implementation and the configuration together by inheriting
from the `BaseModelRegistryFlavor` class. Make sure that you give a `name`
to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml model-registry flavor register <IMAGE-BUILDER-FLAVOR-SOURCE-PATH>
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are 
coming into play in a ZenML workflow.

- The **CustomModelRegistryFlavor** class is imported and utilized upon the 
creation of the custom flavor through the CLI.
- The **CustomModelRegistryConfig** class is imported when someone tries to 
register/update a stack component with this custom flavor. Especially, 
during the registration process of the stack component, the config will be used 
to validate the values given by the user. As `Config` object are inherently 
`pydantic` objects, you can also add your own custom validators here.
- The **CustomModelRegistry** only comes into play when the component is 
ultimately in use. 

The design behind this interaction lets us separate the configuration of the 
flavor from its implementation. This way we can register flavors and components 
even when the major dependencies behind their implementation are not installed
in our local setting (assuming the `CustomModelRegistryFlavor` and the 
`CustomModelRegistryConfig` are implemented in a different module/path than
the actual `CustomModelRegistry`).
{% endhint %}

For a full implementation example, please check out the
[MlflowModelRegistry](https://apidocs.zenml.io/latest/integration_code_docs/integrations-mlflow/#zenml.integrations.mlflow.model_registry.MLFlowModelRegistry)