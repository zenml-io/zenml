#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import TYPE_CHECKING, Any, Optional

import tfx.orchestration.pipeline as tfx_pipeline

from zenml.core.component_factory import orchestrator_store_factory
from zenml.core.repo import Repository
from zenml.enums import OrchestratorTypes
from zenml.integrations.kubeflow.orchestrators.kubeflow_dag_runner import (
    KubeflowDagRunner,
    KubeflowDagRunnerConfig,
)
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline

logger = get_logger(__name__)


@orchestrator_store_factory.register(OrchestratorTypes.kubeflow)
class KubeflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow."""

    docker_image_name: str
    docker_base_image_name: Optional[str] = None

    @property
    def full_docker_image_name(self) -> str:
        """Returns the full docker image name including registry and tag."""
        container_registry = Repository().get_active_stack().container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{self.docker_image_name}"
        else:
            return self.docker_image_name

    def pre_run(self, caller_filepath: str) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        from zenml.utils.docker_utils import (
            build_docker_image,
            push_docker_image,
        )

        image_name = self.full_docker_image_name

        repository_root = Repository().path
        build_docker_image(
            build_context_path=repository_root,
            image_name=image_name,
            requirements=[
                "kubernetes",
                "gcsfs",
            ],  # TODO [HIGH]: get from active artifact store etc.
            base_image=self.docker_base_image_name,
        )

        if Repository().get_active_stack().container_registry:
            push_docker_image(image_name)

    def run(
        self,
        zenml_pipeline: "BasePipeline",
        run_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Prepares the pipeline to be run on Kubeflow"""
        from zenml.utils.docker_utils import get_image_digest

        image_name = self.full_docker_image_name
        image_name = get_image_digest(image_name) or image_name

        config = KubeflowDagRunnerConfig(image=image_name)
        runner = KubeflowDagRunner(config=config)

        # Establish the connections between the components
        zenml_pipeline.connect(**zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = [s.component for s in zenml_pipeline.steps.values()]

        artifact_store = zenml_pipeline.stack.artifact_store
        metadata_store = zenml_pipeline.stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name=zenml_pipeline.name,
            components=steps,  # type: ignore[arg-type]
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=zenml_pipeline.enable_cache,
        )

        output_file = runner.run(created_pipeline)

        import kfp
        import urllib3
        from kubernetes import config

        try:
            # load kubeflow config to authorize the KFP client
            config.load_kube_config()

            # upload the pipeline to Kubeflow and start it
            client = kfp.Client()
            result = client.create_run_from_pipeline_package(
                output_file,
                arguments={},
                run_name=run_name,
                enable_caching=zenml_pipeline.enable_cache,
            )
            logger.info("Started pipeline run with ID '%s'.", result.run_id)
        except urllib3.exceptions.HTTPError as error:
            logger.warning(
                "Failed to upload Kubeflow pipeline: %s. "
                "If you still want to run this pipeline, upload the file '%s' "
                "manually.",
                error,
                output_file,
            )

    @property
    def is_running(self) -> bool:
        """Returns true if the orchestrator is running."""
        return True
