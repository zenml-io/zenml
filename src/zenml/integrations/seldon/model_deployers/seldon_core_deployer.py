#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import List, Optional
from kubernetes import client as client, config as k8s_config
from kubernetes.client.rest import ApiException

from zenml.enums import ModelDeployerFlavor, StackComponentType, ModelDeployerFlavor
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.services import BaseService, ServiceConfig
from zenml.stack.stack_component_class_registry import register_stack_component_class

@register_stack_component_class(
    component_type=StackComponentType.MODEL_DEPLOYER,
    component_flavor=ModelDeployerFlavor.SELDON,
)
class SeldonCoreDeployer(BaseModelDeployer):
    """Seldon Core implementation of the BaseModelDeployer"""

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.MODEL_DEPLOYER

    @property
    def flavor(self) -> ModelDeployerFlavor:
        """The model deployer flavor."""
        return ModelDeployerFlavor.SELDON

    def deploy_model(
        self,
        pipeline_name: str,
        run_id: str,
        step_name: str,
        model_name: str,
        model_uri: str,
        model_type: str,
        config: ServiceConfig,
        kubernetes_context: Optional[str] = None
    ) -> BaseService:
        """

        We assume that the deployment decision is made at the step level and 
        here we have to delete any older services that are running and start 
        a new one.

        This method interacts with external serving platforms that manage services. 
        In Seldon's case this would be the Kubernetes API. Get the SeldonDeployment 
        workload's details and check annotations to know what run resulted in this 
        deployment.Based on the information from that source, we create a new service 
        or keep the older one running and return it.
        
        Concrete model deployer subclasses must implement the following
        functionality in this method:
        - Detect if there is an existing model server instance running serving
        one or more previous versions of the same model
        - Deploy the model to the serving platform or update the existing model
        server instance to include the new model version
        - Return a Service object that is a representation of the external model
        server instance. The Service must implement basic operational state
        tracking and lifecycle management operations for the model server (e.g.
        start, stop, etc.)

        Args:
            pipeline_name: Name of the pipeline that the model to be deployed
                is part of.
            run_id: ID of the pipeline run which the model to be deployed
                is part of.
            step_name: The name of the pipeline model deployment step that
                deploys the model.
            model_name: Name of the model to be deployed.
            model_uri: URI of the model to be deployed.
            model_type: Type/format of the model to be deployed.
            config: Custom Service configuration parameters for the model
                deployer.

        Returns:
            The deployment Service object.
        """

        k8s_config.load_kube_config(context=kubernetes_context)

        k8s_client = client.CustomObjectsApi()
        seldon_deployment_objects = None
        try:
            seldon_deployment_objects = k8s_client.list_cluster_custom_object(
            group="machinelearning.seldon.io", 
            version="v1",
            plural="seldondeployments"
            )
        except ApiException as e:
            print("Exception when listing SeldonDeployment objects: %s\n" % e)
        

        
        
        
    def find_model_server(
        self,
        pipeline_name: Optional[str] = None,
        run_id: Optional[str] = None,
        step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Abstract method to find one or more a model servers that match the
        given criteria.

        Args:
            pipeline_name: Name of the pipeline that the deployed model was part
            of.
            run_id: ID of the pipeline run which the deployed model was part of.
            step_name: The name of the pipeline model deployment step that
                deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """

    def stop_model_server(self) -> None:
        """Abstract method to stop a model server.

        Args:
            ...: The arguments to be passed to the underlying model deployer
                implementation.
        """

    # @abstractmethod
    # def start_model_server(self, ...) -> None:
    #     """Abstract method to start ????? a model server.

    #     Args:
    #         ...: The arguments to be passed to the underlying model deployer
    #             implementation.
    #     """
