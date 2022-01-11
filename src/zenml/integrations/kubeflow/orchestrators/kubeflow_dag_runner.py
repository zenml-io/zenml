# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""The below code is copied from the TFX source repo with minor changes.
All credits goes to  the TFX team for the core implementation"""

import collections
import copy
import os
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    MutableMapping,
    Optional,
    Set,
    Type,
    Union,
)

from kfp import compiler, dsl, gcp
from kubernetes import client as k8s_client
from tfx.dsl.compiler import compiler as tfx_compiler
from tfx.dsl.components.base import base_component as tfx_base_component
from tfx.dsl.components.base import base_node
from tfx.orchestration import data_types
from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration import tfx_runner
from tfx.orchestration.config import pipeline_config
from tfx.orchestration.launcher import (
    base_component_launcher,
    in_process_component_launcher,
    kubernetes_component_launcher,
)
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import telemetry_utils

from zenml.integrations.kubeflow.orchestrators.kubeflow_component import (
    KubeflowComponent,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

# OpFunc represents the type of a function that takes as input a
# dsl.ContainerOp and returns the same object. Common operations such as adding
# k8s secrets, mounting volumes, specifying the use of TPUs and so on can be
# specified as an OpFunc.
# See example usage here:
# https://github.com/kubeflow/pipelines/blob/master/sdk/python/kfp/gcp.py
OpFunc = Callable[[dsl.ContainerOp], Union[dsl.ContainerOp, None]]

# Default secret name for GCP credentials. This secret is installed as part of
# a typical Kubeflow installation when the component is GKE.
_KUBEFLOW_GCP_SECRET_NAME = "user-gcp-sa"


def _mount_config_map_op(config_map_name: str) -> OpFunc:
    """Mounts all key-value pairs found in the named Kubernetes ConfigMap.
    All key-value pairs in the ConfigMap are mounted as environment variables.
    Args:
      config_map_name: The name of the ConfigMap resource.
    Returns:
      An OpFunc for mounting the ConfigMap.
    """

    def mount_config_map(container_op: dsl.ContainerOp) -> None:
        """Mounts all key-value pairs found in the Kubernetes ConfigMap."""
        config_map_ref = k8s_client.V1ConfigMapEnvSource(
            name=config_map_name, optional=True
        )
        container_op.container.add_env_from(
            k8s_client.V1EnvFromSource(config_map_ref=config_map_ref)
        )

    return mount_config_map


def _mount_secret_op(secret_name: str) -> OpFunc:
    """Mounts all key-value pairs found in the named Kubernetes Secret.
    All key-value pairs in the Secret are mounted as environment variables.
    Args:
      secret_name: The name of the Secret resource.
    Returns:
      An OpFunc for mounting the Secret.
    """

    def mount_secret(container_op: dsl.ContainerOp) -> None:
        """Mounts all key-value pairs found in the named Kubernetes Secret."""
        secret_ref = k8s_client.V1ConfigMapEnvSource(
            name=secret_name, optional=True
        )

        container_op.container.add_env_from(
            k8s_client.V1EnvFromSource(secret_ref=secret_ref)
        )

    return mount_secret


def get_default_pipeline_operator_funcs(
    use_gcp_sa: bool = False,
) -> List[OpFunc]:
    """Returns a default list of pipeline operator functions.
    Args:
      use_gcp_sa: If true, mount a GCP service account secret to each pod, with
        the name _KUBEFLOW_GCP_SECRET_NAME.
    Returns:
      A list of functions with type OpFunc.
    """
    # Enables authentication for GCP services if needed.
    gcp_secret_op = gcp.use_gcp_secret(_KUBEFLOW_GCP_SECRET_NAME)

    # Mounts configmap containing Metadata gRPC server configuration.
    mount_config_map_op = _mount_config_map_op("metadata-grpc-configmap")
    if use_gcp_sa:
        return [gcp_secret_op, mount_config_map_op]
    else:
        return [mount_config_map_op]


def get_default_pod_labels() -> Dict[str, str]:
    """Returns the default pod label dict for Kubeflow."""
    # KFP default transformers add pod env:
    # https://github.com/kubeflow/pipelines/blob/0.1.32/sdk/python/kfp/compiler/_default_transformers.py
    result = {"add-pod-env": "true", telemetry_utils.LABEL_KFP_SDK_ENV: "tfx"}
    return result


class KubeflowDagRunnerConfig(pipeline_config.PipelineConfig):
    """Runtime configuration parameters specific to execution on Kubeflow."""

    def __init__(
        self,
        image: str,
        pipeline_operator_funcs: Optional[List[OpFunc]] = None,
        supported_launcher_classes: Optional[
            List[Type[base_component_launcher.BaseComponentLauncher]]
        ] = None,
        metadata_ui_path: str = "/tmp/mlpipeline-ui-metadata.json",
        **kwargs: Any
    ):
        """Creates a KubeflowDagRunnerConfig object.
        The user can use pipeline_operator_funcs to apply modifications to
        ContainerOps used in the pipeline. For example, to ensure the pipeline
        steps mount a GCP secret, and a Persistent Volume, one can create config
        object like so:
          from kfp import gcp, onprem
          mount_secret_op = gcp.use_secret('my-secret-name)
          mount_volume_op = onprem.mount_pvc(
            "my-persistent-volume-claim",
            "my-volume-name",
            "/mnt/volume-mount-path")
          config = KubeflowDagRunnerConfig(
            pipeline_operator_funcs=[mount_secret_op, mount_volume_op]
          )
        Args:
          image: The docker image to use in the pipeline.
          pipeline_operator_funcs: A list of ContainerOp modifying functions that
            will be applied to every container step in the pipeline.
          supported_launcher_classes: A list of component launcher classes that are
            supported by the current pipeline. List sequence determines the order in
            which launchers are chosen for each component being run.
          metadata_ui_path: File location for metadata-ui-metadata.json file.
          **kwargs: keyword args for PipelineConfig.
        """
        supported_launcher_classes = supported_launcher_classes or [
            in_process_component_launcher.InProcessComponentLauncher,
            kubernetes_component_launcher.KubernetesComponentLauncher,
        ]
        super().__init__(
            supported_launcher_classes=supported_launcher_classes, **kwargs
        )
        self.pipeline_operator_funcs = (
            pipeline_operator_funcs or get_default_pipeline_operator_funcs()
        )
        self.image = image
        self.metadata_ui_path = metadata_ui_path


class KubeflowDagRunner(tfx_runner.TfxRunner):
    """Kubeflow Pipelines runner.
    Constructs a pipeline definition YAML file based on the TFX logical pipeline.
    """

    def __init__(
        self,
        config: KubeflowDagRunnerConfig,
        output_path: str,
        pod_labels_to_attach: Optional[Dict[str, str]] = None,
    ):
        """Initializes KubeflowDagRunner for compiling a Kubeflow Pipeline.
        Args:
          config: A KubeflowDagRunnerConfig object to specify runtime
            configuration when running the pipeline under Kubeflow.
          output_path: Path where the pipeline definition file will be stored.
          pod_labels_to_attach: Optional set of pod labels to attach to GKE pod
            spinned up for this pipeline. Default to the 3 labels:
            1. add-pod-env: true,
            2. pipeline SDK type,
            3. pipeline unique ID,
            where 2 and 3 are instrumentation of usage tracking.
        """
        super().__init__(config)
        self._kubeflow_config = config
        self._output_path = output_path
        self._compiler = compiler.Compiler()
        self._tfx_compiler = tfx_compiler.Compiler()
        self._params: List[dsl.PipelineParam] = []
        self._params_by_component_id: Dict[
            str, List[data_types.RuntimeParameter]
        ] = collections.defaultdict(list)
        self._deduped_parameter_names: Set[str] = set()
        self._pod_labels_to_attach = (
            pod_labels_to_attach or get_default_pod_labels()
        )

    def _parse_parameter_from_component(
        self, component: tfx_base_component.BaseComponent
    ) -> None:
        """Extract embedded RuntimeParameter placeholders from a component.
        Extract embedded RuntimeParameter placeholders from a component, then append
        the corresponding dsl.PipelineParam to KubeflowDagRunner.
        Args:
          component: a TFX component.
        """

        deduped_parameter_names_for_component = set()
        for parameter in component.exec_properties.values():
            if not isinstance(parameter, data_types.RuntimeParameter):
                continue
            # Ignore pipeline root because it will be added later.
            if parameter.name == tfx_pipeline.ROOT_PARAMETER.name:
                continue
            if parameter.name in deduped_parameter_names_for_component:
                continue

            deduped_parameter_names_for_component.add(parameter.name)
            self._params_by_component_id[component.id].append(parameter)
            if parameter.name not in self._deduped_parameter_names:
                self._deduped_parameter_names.add(parameter.name)
                dsl_parameter = dsl.PipelineParam(
                    name=parameter.name, value=str(parameter.default)
                )
                self._params.append(dsl_parameter)

    def _parse_parameter_from_pipeline(
        self, pipeline: tfx_pipeline.Pipeline
    ) -> None:
        """Extract all the RuntimeParameter placeholders from the pipeline."""

        for component in pipeline.components:
            self._parse_parameter_from_component(component)

    def _construct_pipeline_graph(
        self, pipeline: tfx_pipeline.Pipeline
    ) -> None:
        """Constructs a Kubeflow Pipeline graph.
        Args:
          pipeline: The logical TFX pipeline to base the construction on.
          pipeline_root: dsl.PipelineParam representing the pipeline root.
        """
        component_to_kfp_op: Dict[base_node.BaseNode, dsl.ContainerOp] = {}
        tfx_ir = self._generate_tfx_ir(pipeline)

        # Assumption: There is a partial ordering of components in the list,
        # i.e. if component A depends on component B and C, then A appears
        # after B and C in the list.
        for component in pipeline.components:
            # Keep track of the set of upstream dsl.ContainerOps for this
            # component.
            depends_on = set()

            for upstream_component in component.upstream_nodes:
                depends_on.add(component_to_kfp_op[upstream_component])

            # remove the extra pipeline node information
            tfx_node_ir = self._dehydrate_tfx_ir(tfx_ir, component.id)

            from zenml.utils import source_utils

            main_module_file = sys.modules["__main__"].__file__
            main_module = source_utils.get_module_source_from_file_path(
                os.path.abspath(main_module_file)
            )

            step_module = component.component_type.split(".")[:-1]
            if step_module[0] == "__main__":
                step_module = main_module
            else:
                step_module = ".".join(step_module)

            kfp_component = KubeflowComponent(
                main_module=main_module,
                step_module=step_module,
                step_function_name=component.id,
                component=component,
                depends_on=depends_on,
                image=self._kubeflow_config.image,
                pod_labels_to_attach=self._pod_labels_to_attach,
                tfx_ir=tfx_node_ir,
                metadata_ui_path=self._kubeflow_config.metadata_ui_path,
                runtime_parameters=self._params_by_component_id[component.id],
            )

            for operator in self._kubeflow_config.pipeline_operator_funcs:
                kfp_component.container_op.apply(operator)

            component_to_kfp_op[component] = kfp_component.container_op

    def _del_unused_field(
        self, node_id: str, message_dict: MutableMapping[str, Any]
    ) -> None:
        """Remove fields that are not used by the pipeline."""
        for item in list(message_dict.keys()):
            if item != node_id:
                del message_dict[item]

    def _dehydrate_tfx_ir(
        self, original_pipeline: pipeline_pb2.Pipeline, node_id: str  # type: ignore[valid-type] # noqa
    ) -> pipeline_pb2.Pipeline:  # type: ignore[valid-type]
        """Dehydrate the TFX IR to remove unused fields."""
        pipeline = copy.deepcopy(original_pipeline)
        for node in pipeline.nodes:  # type: ignore[attr-defined]
            if (
                node.WhichOneof("node") == "pipeline_node"
                and node.pipeline_node.node_info.id == node_id
            ):
                del pipeline.nodes[:]  # type: ignore[attr-defined]
                pipeline.nodes.extend([node])  # type: ignore[attr-defined]
                break

        deployment_config = pipeline_pb2.IntermediateDeploymentConfig()
        pipeline.deployment_config.Unpack(deployment_config)  # type: ignore[attr-defined] # noqa
        self._del_unused_field(node_id, deployment_config.executor_specs)
        self._del_unused_field(node_id, deployment_config.custom_driver_specs)
        self._del_unused_field(
            node_id, deployment_config.node_level_platform_configs
        )
        pipeline.deployment_config.Pack(deployment_config)  # type: ignore[attr-defined] # noqa
        return pipeline

    def _generate_tfx_ir(
        self, pipeline: tfx_pipeline.Pipeline
    ) -> Optional[pipeline_pb2.Pipeline]:  # type: ignore[valid-type]
        """Generate the TFX IR from the logical TFX pipeline."""
        result = self._tfx_compiler.compile(pipeline)
        return result

    def run(self, pipeline: tfx_pipeline.Pipeline) -> None:
        """Compiles and outputs a Kubeflow Pipeline YAML definition file.
        Args:
          pipeline: The logical TFX pipeline to use when building the Kubeflow
            pipeline.
        """
        for component in pipeline.components:
            # TODO(b/187122662): Pass through pip dependencies as a first-class
            # component flag.
            if isinstance(component, tfx_base_component.BaseComponent):
                component._resolve_pip_dependencies(
                    # pylint: disable=protected-access
                    pipeline.pipeline_info.pipeline_root
                )

        def _construct_pipeline() -> None:
            """Creates Kubeflow ContainerOps for each TFX component
            encountered in the pipeline definition."""
            self._construct_pipeline_graph(pipeline)

        # Need to run this first to get self._params populated. Then KFP
        # compiler can correctly match default value with PipelineParam.
        self._parse_parameter_from_pipeline(pipeline)
        # Create workflow spec and write out to package.
        self._compiler._create_and_write_workflow(
            # pylint: disable=protected-access
            pipeline_func=_construct_pipeline,
            pipeline_name=pipeline.pipeline_info.pipeline_name,
            params_list=self._params,
            package_path=self._output_path,
        )
        logger.info(
            "Finished writing kubeflow pipeline definition file '%s'.",
            self._output_path,
        )
