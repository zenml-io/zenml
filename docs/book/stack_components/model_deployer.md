---
description: Manage the models deployed by your pipelines
---

Model deployers are stack components responsible for online model serving.
Online serving is the process of hosting and loading machine-learning models 
as part of a managed web service and providing access to the models through 
an API endpoint like HTTP or GRPC. Once deployed, you can send inference 
requests to the model through the web service's API and receive fast, 
low-latency responses.

When present in a stack, the model deployer also acts as a registry for models
that are served with ZenML. You can use the model deployer to list all 
models that are currently deployed for online inference or filtered according 
to a particular pipeline run or step, or to suspend, resume or delete an 
external model server managed through ZenML.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](./introduction.md).  
{% endhint %}

## Base Abstraction

The base abstraction of the model deployer serves three major purposes:

1. It contains all the stack related configuration attributes required to
    interact with the remote model serving tool, service or platform (e.g.
    hostnames, URLs, references to credentials, other client related
    configuration parameters).
    
2. It implements the continuous deployment logic necessary to deploy models
    in a way that updates an existing model server that is already serving a
    previous version of the same model instead of creating a new model server
    for every new model version (see the `deploy_model` abstract method).
    This functionality can be consumed directly from ZenML pipeline steps, but
    it can also be used outside the pipeline to deploy ad-hoc models. It is
    also usually coupled with a standard model deployer step, implemented by
    each integration, that hides the details of the deployment process away from
    the user.
    
3. It acts as a ZenML BaseService registry, where every BaseService instance
    is used as an internal representation of a remote model server (see the
    `find_model_server` abstract method). To achieve this, it must be able to
    re-create the configuration of a BaseService from information that is
    persisted externally, alongside or even part of the remote model server
    configuration itself. For example, for model servers that are implemented as
    Kubernetes resources, the BaseService instances can be serialized and saved
    as Kubernetes resource annotations. This allows the model deployer to keep
    track of all externally running model servers and to re-create their
    corresponding BaseService instance representations at any given time.
    The model deployer also defines methods that implement basic life-cycle
    management on remote model servers outside the coverage of a pipeline
    (see `stop_model_server`, `start_model_server` and `delete_model_server`).


```python
from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generator, List, Optional
from uuid import UUID

from zenml.enums import StackComponentType
from zenml.services import BaseService, ServiceConfig
from zenml.stack import StackComponent

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BaseModelDeployer(StackComponent, ABC):
    """Base class for all ZenML model deployers."""

    # Class variables
    TYPE: ClassVar[StackComponentType] = StackComponentType.MODEL_DEPLOYER

    @abstractmethod
    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Abstract method to deploy a model."""

    @staticmethod
    @abstractmethod
    def get_model_server_info(
        service: BaseService,
    ) -> Dict[str, Optional[str]]:
        """Give implementation specific way to extract relevant model server
        properties for the user."""

    @abstractmethod
    def find_model_server(
        self,
        running: bool = False,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Abstract method to find one or more a model servers that match the
        given criteria."""

    @abstractmethod
    def stop_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to stop a model server."""

    @abstractmethod
    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        """Abstract method to start a model server."""

    @abstractmethod
    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to delete a model server."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the source code on GitHub.
{% endhint %}


## List of available model deployers

|                     | Flavor | Integration |
|---------------------|--------|-------------|
| MLFlowModelDeployer  | mlflow  | mlflow  |
| SeldonModelDeployer     | seldon     | seldon          |

## Building your own model deployers

WIP

