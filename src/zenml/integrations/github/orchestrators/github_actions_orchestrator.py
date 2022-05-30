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

import os
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Tuple

from git.exc import InvalidGitRepositoryError
from git.repo.base import Repo
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.integrations.github.orchestrators.github_actions_entrypoint_configuration import (
    GithubActionsEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.utils import yaml_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

from zenml.enums import StackComponentType
from zenml.integrations.github import GITHUB_ORCHESTRATOR_FLAVOR
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.utils import docker_utils, source_utils

logger = get_logger(__name__)

# TODO: b64 encoding
# TODO: run name
# TODO: secrets
# TODO: container registry user/pw


class GithubActionsOrchestrator(BaseOrchestrator):
    prevent_dirty_repository: bool = True
    push: bool = False

    _git_repo: Repo

    # Class configuration
    FLAVOR: ClassVar[str] = GITHUB_ORCHESTRATOR_FLAVOR

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        try:
            self._git_repo = Repo(search_parent_directories=True)
        except InvalidGitRepositoryError:
            raise RuntimeError("No git repo found")

        remote_url = self._git_repo.remote().url

        if remote_url.startswith("git@github.com") or remote_url.startswith(
            "https://github.com"
        ):
            pass
        else:
            raise RuntimeError("Not a github repo")

    @property
    def workflow_directory(self) -> str:
        """Returns path to a directory in which the github workflows are stored."""
        return os.path.join(self._git_repo.working_dir, ".github", "workflows")

    @property
    def validator(self) -> Optional[StackValidator]:
        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.is_local:
                return False, ""

            for component in stack.components.values():
                if component.local_path:
                    return False, ""

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_local_requirements,
        )

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""
        container_registry = Repository().active_stack.container_registry
        assert container_registry  # should never happen due to validation

        base_image_name = f"zenml-github-actions:{pipeline_name}"
        return f"{container_registry.uri.rstrip('/')}/{base_image_name}"

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        if self.prevent_dirty_repository and self._git_repo.is_dirty(
            untracked_files=True
        ):
            raise RuntimeError("")

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug(
            "Github actions docker container requirements: %s", requirements
        )

        docker_utils.build_docker_image(
            build_context_path=source_utils.get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
        )

        assert stack.container_registry  # should never happen due to validation
        stack.container_registry.push_image(image_name)

        # Store the docker image digest in the runtime configuration so it gets
        # tracked in the ZenStore
        image_digest = docker_utils.get_image_digest(image_name) or image_name
        runtime_configuration["docker_image"] = image_digest

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        workflow_path = os.path.join(
            self.workflow_directory, f"{pipeline.name}.yaml"
        )

        workflow_dict = {"name": pipeline.name}

        schedule = runtime_configuration.schedule
        if schedule:
            # TODO: warn that it only works once merged to the main branch
            # TODO: only cron schedule, >= 5 min
            raise
        else:
            # The pipeline should only run once. The only fool-proof way to
            # only execute a workflow once seems to be running on specific tags.
            # We don't want to create tags for each pipeline run though, so
            # instead we only run this workflow if the workflow file is
            # modified. As long as users don't manually modify these files this
            # should be sufficient.
            workflow_path_in_repo = os.path.relpath(
                workflow_path, self.workflow_directory
            )
            workflow_dict["on"] = {"push": {"paths": [workflow_path_in_repo]}}

        jobs = {}
        for step in sorted_steps:
            # docker_login_step = {
            #     "uses": "docker/login-action@v1",
            #     "with": {
            #         "registry": stack.container_registry.uri,
            #         "username": "{{ github.actor }}",
            #         "password": "{{ secrets.GITHUB_TOKEN }}",
            #     },
            # }
            image_name = self.get_docker_image_name(pipeline.name)
            image_name = docker_utils.get_image_digest(image_name) or image_name

            command = [
                "docker",
                "run",
                image_name,
                *GithubActionsEntrypointConfiguration.get_entrypoint_command(),
                *GithubActionsEntrypointConfiguration.get_entrypoint_arguments(
                    step=step, pb2_pipeline=pb2_pipeline
                ),
            ]
            docker_run_step = {"run": " ".join(command)}
            job_dict = {
                "runs-on": "ubuntu-latest",
                "needs": self.get_upstream_step_names(
                    step=step, pb2_pipeline=pb2_pipeline
                ),
                "steps": [docker_run_step],
            }
            jobs[step.name] = job_dict

        workflow_dict["jobs"] = jobs

        fileio.makedirs(self.workflow_directory)
        yaml_utils.write_yaml(workflow_path, workflow_dict, sort_keys=False)

        if self.push:
            # Add, commit and push the pipeline worflow yaml
            self._git_repo.index.add(workflow_path)
            self._git_repo.index.commit(
                f"[ZenML GitHub Actions Orchestrator] Add github workflow for pipeline {pipeline.name}."
            )
            self._git_repo.remote().push()
