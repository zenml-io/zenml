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

import os
from typing import TYPE_CHECKING, Any, List, Optional

import click
import kfp
import tfx.orchestration.pipeline as tfx_pipeline
import urllib3
from kubernetes import config

from zenml.constants import APP_NAME
from zenml.core.component_factory import orchestrator_store_factory
from zenml.core.repo import Repository
from zenml.enums import OrchestratorTypes
from zenml.integrations.kubeflow.orchestrators.kubeflow_dag_runner import (
    KubeflowDagRunner,
    KubeflowDagRunnerConfig,
)
from zenml.integrations.utils import get_requirements_for_module
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline

logger = get_logger(__name__)


@orchestrator_store_factory.register(OrchestratorTypes.kubeflow)
class KubeflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow."""

    docker_image_name: str
    custom_docker_base_image_name: Optional[str] = None

    @property
    def full_docker_image_name(self) -> str:
        """Returns the full docker image name including registry and tag."""
        container_registry = Repository().get_active_stack().container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{self.docker_image_name}"
        else:
            return self.docker_image_name

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipeline files
        are stored."""
        directory = os.path.join(
            click.get_app_dir(APP_NAME), "kubeflow_pipelines", str(self.uuid)
        )
        fileio.make_dirs(directory)
        return directory

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
        requirements = ["kubernetes"] + self._get_stack_requirements()

        build_docker_image(
            build_context_path=repository_root,
            image_name=image_name,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
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

        from zenml.utils.docker_utils import get_image_digest

        image_name = self.full_docker_image_name
        image_name = get_image_digest(image_name) or image_name

        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{zenml_pipeline.name}.yaml"
        )
        runner_config = KubeflowDagRunnerConfig(image=image_name)
        runner = KubeflowDagRunner(
            config=runner_config, output_path=pipeline_file_path
        )
        runner.run(created_pipeline)

        self._upload_and_run_pipeline(
            pipeline_file_path=pipeline_file_path,
            run_name=run_name,
            enable_cache=zenml_pipeline.enable_cache,
        )

    def _upload_and_run_pipeline(
        self, pipeline_file_path: str, run_name: str, enable_cache: bool
    ):
        """Tries to upload and run a KFP pipeline.

        Args:
            pipeline_file_path: Path to the pipeline definition file.
            run_name: A name for the pipeline run that will be started.
            enable_cache: Whether caching is enabled for this pipeline run.
        """
        try:
            # load kubeflow config to authorize the KFP client
            config.load_kube_config()

            # upload the pipeline to Kubeflow and start it
            client = kfp.Client()
            result = client.create_run_from_pipeline_package(
                pipeline_file_path,
                arguments={},
                run_name=run_name,
                enable_caching=enable_cache,
            )
            logger.info("Started pipeline run with ID '%s'.", result.run_id)
        except urllib3.exceptions.HTTPError as error:
            logger.warning(
                "Failed to upload Kubeflow pipeline: %s. "
                "If you still want to run this pipeline, upload the file '%s' "
                "manually.",
                error,
                pipeline_file_path,
            )

    def _get_stack_requirements(self) -> List[str]:
        """Gets list of requirements for the current active stack."""
        stack = Repository().get_active_stack()
        requirements = []

        artifact_store_module = stack.artifact_store.__module__
        requirements += get_requirements_for_module(artifact_store_module)

        metadata_store_module = stack.metadata_store.__module__
        requirements += get_requirements_for_module(metadata_store_module)

        return requirements

    @property
    def is_running(self) -> bool:
        """Returns true if the orchestrator is running."""
        return True
