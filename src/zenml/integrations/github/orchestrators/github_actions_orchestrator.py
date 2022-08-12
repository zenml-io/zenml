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
"""Implementation of the GitHub Actions Orchestrator."""

import copy
import os
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

from git.exc import InvalidGitRepositoryError
from git.repo.base import Repo
from google.protobuf import json_format
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.container_registries import (
    BaseContainerRegistry,
    GitHubContainerRegistry,
)
from zenml.entrypoints.step_entrypoint_configuration import PIPELINE_JSON_OPTION
from zenml.integrations.github.orchestrators.github_actions_entrypoint_configuration import (
    GitHubActionsEntrypointConfiguration,
)
from zenml.integrations.github.secrets_managers.github_secrets_manager import (
    ENV_IN_GITHUB_ACTIONS,
    GitHubSecretsManager,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.utils import deprecation_utils, string_utils, yaml_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

from zenml.enums import StackComponentType
from zenml.integrations.github import GITHUB_ORCHESTRATOR_FLAVOR
from zenml.stack import StackValidator

logger = get_logger(__name__)

# Git remote URL prefixes that indicate a GitHub repository.
GITHUB_REMOTE_URL_PREFIXES = ["git@github.com", "https://github.com"]
# Name of the GitHub Action used to login to docker
DOCKER_LOGIN_ACTION = "docker/login-action@v1"
# Name of the environment variable that holds the encoded pb2 pipeline
ENV_ENCODED_ZENML_PIPELINE = "ENCODED_ZENML_PIPELINE"


class GitHubActionsOrchestrator(BaseOrchestrator, PipelineDockerImageBuilder):
    """Orchestrator responsible for running pipelines using GitHub Actions.

    Attributes:
        custom_docker_base_image_name: Name of a docker image that should be
            used as the base for the image that will be run on GitHub Action
            runners. If no custom image is given, a basic image of the active
            ZenML version will be used. **Note**: This image needs to have
            ZenML installed, otherwise the pipeline execution will fail. For
            that reason, you might want to extend the ZenML docker images
            found here: https://hub.docker.com/r/zenmldocker/zenml/
        skip_dirty_repository_check: If `True`, this orchestrator will not
            raise an exception when trying to run a pipeline while there are
            still untracked/uncommitted files in the git repository.
        skip_github_repository_check: If `True`, the orchestrator will not check
            if your git repository is pointing to a GitHub remote.
        push: If `True`, this orchestrator will automatically commit and push
            the GitHub workflow file when running a pipeline. If `False`, the
            workflow file will be written to the correct location but needs to
            be committed and pushed manually.
    """

    custom_docker_base_image_name: Optional[str] = None
    skip_dirty_repository_check: bool = False
    skip_github_repository_check: bool = False
    push: bool = False

    _git_repo: Optional[Repo] = None

    # Class configuration
    FLAVOR: ClassVar[str] = GITHUB_ORCHESTRATOR_FLAVOR

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("custom_docker_base_image_name", "docker_parent_image")
    )

    @property
    def git_repo(self) -> Repo:
        """Returns the git repository for the current working directory.

        Returns:
            Git repository for the current working directory.

        Raises:
            RuntimeError: If there is no git repository for the current working
                directory or the repository remote is not pointing to GitHub.
        """
        if not self._git_repo:
            try:
                self._git_repo = Repo(search_parent_directories=True)
            except InvalidGitRepositoryError:
                raise RuntimeError(
                    "Unable to find git repository in current working "
                    f"directory {os.getcwd()} or its parent directories."
                )

            remote_url = self.git_repo.remote().url
            is_github_repo = any(
                remote_url.startswith(prefix)
                for prefix in GITHUB_REMOTE_URL_PREFIXES
            )
            if not (is_github_repo or self.skip_github_repository_check):
                raise RuntimeError(
                    f"The remote URL '{remote_url}' of your git repo "
                    f"({self._git_repo.git_dir}) is not pointing to a GitHub "
                    "repository. The GitHub Actions orchestrator runs "
                    "pipelines using GitHub Actions and therefore only works "
                    "with GitHub repositories. If you want to skip this check "
                    "and run this orchestrator anyway, run: \n"
                    f"`zenml orchestrator update {self.name} "
                    "--skip_github_repository_check=true`"
                )

        return self._git_repo

    @property
    def workflow_directory(self) -> str:
        """Returns path to the GitHub workflows directory.

        Returns:
            The GitHub workflows directory.
        """
        assert self.git_repo.working_dir
        return os.path.join(self.git_repo.working_dir, ".github", "workflows")

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validator that ensures that the stack is compatible.

        Makes sure that the stack contains a container registry and only
        remote components.

        Returns:
            The stack validator.
        """

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.is_local:
                return False, (
                    "The GitHub Actions orchestrator requires a remote "
                    f"container registry, but the '{container_registry.name}' "
                    "container registry of your active stack points to a local "
                    f"URI '{container_registry.uri}'. Please make sure stacks "
                    "with a GitHub Actions orchestrator always contain remote "
                    "container registries."
                )

            if container_registry.requires_authentication:
                return False, (
                    "The GitHub Actions orchestrator currently only works with "
                    "GitHub container registries or public container "
                    f"registries, but your {container_registry.FLAVOR} "
                    f"container registry '{container_registry.name}' requires "
                    "authentication."
                )

            for component in stack.components.values():
                if component.local_path:
                    return False, (
                        "The GitHub Actions orchestrator runs pipelines on "
                        "remote GitHub Actions runners, but the "
                        f"'{component.name}' {component.TYPE.value} of your "
                        "active stack is a local component. Please make sure "
                        "to only use remote stack components in combination "
                        "with the GitHub Actions orchestrator. "
                    )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_local_requirements,
        )

    def _docker_login_step(
        self,
        container_registry: BaseContainerRegistry,
    ) -> Optional[Dict[str, Any]]:
        """GitHub Actions step for authenticating with the container registry.

        Args:
            container_registry: The container registry which (potentially)
                requires a step to authenticate.

        Returns:
            Dictionary specifying the GitHub Actions step for authenticating
            with the container registry if that is required, `None` otherwise.
        """
        if (
            isinstance(container_registry, GitHubContainerRegistry)
            and container_registry.automatic_token_authentication
        ):
            # Use GitHub Actions specific placeholder if the container registry
            # specifies automatic token authentication
            username = "${{ github.actor }}"
            password = "${{ secrets.GITHUB_TOKEN }}"
        # TODO: Uncomment these lines once we support different private
        #  container registries in GitHub Actions
        # elif container_registry.requires_authentication:
        #     username = cast(str, container_registry.username)
        #     password = cast(str, container_registry.password)
        else:
            return None

        return {
            "name": "Authenticate with the container registry",
            "uses": DOCKER_LOGIN_ACTION,
            "with": {
                "registry": container_registry.uri,
                "username": username,
                "password": password,
            },
        }

    def _write_environment_file_step(
        self,
        file_name: str,
        secrets_manager: Optional[BaseSecretsManager] = None,
    ) -> Optional[Dict[str, Any]]:
        """GitHub Actions step for writing secrets to an environment file.

        Args:
            file_name: Name of the environment file that should be written.
            secrets_manager: Secrets manager that will be used to read secrets
                during pipeline execution.

        Returns:
            Dictionary specifying the GitHub Actions step for writing the
            environment file.
        """
        if not isinstance(secrets_manager, GitHubSecretsManager):
            return None

        # Always include the environment variable that specifies whether
        # we're running in a GitHub Action workflow so the secret manager knows
        # how to query secret values
        command = (
            f'echo {ENV_IN_GITHUB_ACTIONS}="${ENV_IN_GITHUB_ACTIONS}" '
            f"> {file_name}; "
        )

        # Write all ZenML secrets into the environment file. Explicitly writing
        # these `${{ secrets.<SECRET_NAME> }}` placeholders into the workflow
        # yaml is the only way for us to access the GitHub secrets in a GitHub
        # Actions workflow.
        append_secret_placeholder = (
            "echo {secret_name}=${{{{ secrets.{secret_name} }}}} >> {file}; "
        )
        for secret_name in secrets_manager.get_all_secret_keys(
            include_prefix=True
        ):
            command += append_secret_placeholder.format(
                secret_name=secret_name, file=file_name
            )

        return {
            "name": "Write environment file",
            "run": command,
        }

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds and uploads a docker image.

        Args:
            pipeline: The pipeline for which the image is built.
            stack: The stack on which the pipeline will be executed.
            runtime_configuration: Runtime configuration for the pipeline run.

        Raises:
            RuntimeError: If the orchestrator should only run in a clean git
                repository and the repository is dirty.
        """
        if not self.skip_dirty_repository_check and self.git_repo.is_dirty(
            untracked_files=True
        ):
            raise RuntimeError(
                "Trying to run a pipeline from within a dirty (=containing "
                "untracked/uncommitted files) git repository."
                "If you want this orchestrator to skip the dirty repo check in "
                f"the future, run\n `zenml orchestrator update {self.name} "
                "--skip_dirty_repository_check=true`"
            )

        self.build_and_push_docker_image(
            pipeline_name=pipeline.name,
            docker_configuration=pipeline.docker_configuration,
            stack=stack,
            runtime_configuration=runtime_configuration,
        )

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Writes a GitHub Action workflow yaml and optionally pushes it.

        Args:
             sorted_steps: List of sorted steps
             pipeline: Zenml Pipeline instance
             pb2_pipeline: Protobuf Pipeline instance
             stack: The stack the pipeline was run on
             runtime_configuration: The Runtime configuration of the current run

        Raises:
            ValueError: If a schedule without a cron expression or with an
                invalid cron expression is passed.
        """
        schedule = runtime_configuration.schedule

        workflow_name = pipeline.name
        if schedule:
            # Add a suffix to the workflow filename so we don't overwrite
            # scheduled pipeline by future schedules or single pipeline runs.
            datetime_string = datetime.now().strftime("%y_%m_%d_%H_%M_%S")
            workflow_name += f"-scheduled-{datetime_string}"

        workflow_path = os.path.join(
            self.workflow_directory,
            f"{workflow_name}.yaml",
        )

        # Store the encoded pb2 pipeline once as an environment variable.
        # We will replace the entrypoint argument later to reduce the size
        # of the workflow file.
        encoded_pb2_pipeline = string_utils.b64_encode(
            json_format.MessageToJson(pb2_pipeline)
        )
        workflow_dict: Dict[str, Any] = {
            "name": workflow_name,
            "env": {ENV_ENCODED_ZENML_PIPELINE: encoded_pb2_pipeline},
        }

        if schedule:
            if not schedule.cron_expression:
                raise ValueError(
                    "GitHub Action workflows can only be scheduled using cron "
                    "expressions and not using a periodic schedule. If you "
                    "want to schedule pipelines using this GitHub Action "
                    "orchestrator, please include a cron expression in your "
                    "schedule object. For more information on GitHub workflow "
                    "schedules check out https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule."
                )

            # GitHub workflows requires a schedule interval of at least 5
            # minutes. Invalid cron expressions would be something like
            # `*/3 * * * *` (all stars except the first part of the expression,
            # which will have the format `*/minute_interval`)
            if re.fullmatch(r"\*/[1-4]( \*){4,}", schedule.cron_expression):
                raise ValueError(
                    "GitHub workflows requires a schedule interval of at "
                    "least 5 minutes which is incompatible with your cron "
                    f"expression '{schedule.cron_expression}'. An example of a "
                    "valid cron expression would be '* 1 * * *' to run "
                    "every hour. For more information on GitHub workflow "
                    "schedules check out https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule."
                )

            logger.warning(
                "GitHub only runs scheduled workflows once the "
                "workflow file is merged to the default branch of the "
                "repository (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches#about-the-default-branch). "
                "Please make sure to merge your current branch into the "
                "default branch for this scheduled pipeline to run."
            )
            workflow_dict["on"] = {
                "schedule": [{"cron": schedule.cron_expression}]
            }
        else:
            # The pipeline should only run once. The only fool-proof way to
            # only execute a workflow once seems to be running on specific tags.
            # We don't want to create tags for each pipeline run though, so
            # instead we only run this workflow if the workflow file is
            # modified. As long as users don't manually modify these files this
            # should be sufficient.
            workflow_path_in_repo = os.path.relpath(
                workflow_path, self.git_repo.working_dir
            )
            workflow_dict["on"] = {"push": {"paths": [workflow_path_in_repo]}}

        image_name = runtime_configuration["docker_image"]

        # Prepare the step that writes an environment file which will get
        # passed to the docker image
        env_file_name = ".zenml_docker_env"
        write_env_file_step = self._write_environment_file_step(
            file_name=env_file_name, secrets_manager=stack.secrets_manager
        )
        docker_run_args = (
            ["--env-file", env_file_name] if write_env_file_step else []
        )

        # Prepare the docker login step if necessary
        container_registry = stack.container_registry
        assert container_registry
        docker_login_step = self._docker_login_step(container_registry)

        # The base command that each job will execute with specific arguments
        base_command = [
            "docker",
            "run",
            *docker_run_args,
            image_name,
        ] + GitHubActionsEntrypointConfiguration.get_entrypoint_command()

        jobs = {}
        for step in sorted_steps:
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the "
                    "GitHub Actions orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step.name,
                )

            job_steps = []

            # Copy the shared dicts here to avoid creating yaml anchors (which
            # are currently not supported in GitHub workflow yaml files)
            if write_env_file_step:
                job_steps.append(copy.deepcopy(write_env_file_step))

            if docker_login_step:
                job_steps.append(copy.deepcopy(docker_login_step))

            entrypoint_args = (
                GitHubActionsEntrypointConfiguration.get_entrypoint_arguments(
                    step=step,
                    pb2_pipeline=pb2_pipeline,
                )
            )

            # Replace the encoded string by a global environment variable to
            # keep the workflow file small
            index = entrypoint_args.index(f"--{PIPELINE_JSON_OPTION}")
            entrypoint_args[index + 1] = f"${ENV_ENCODED_ZENML_PIPELINE}"

            command = base_command + entrypoint_args
            docker_run_step = {
                "name": "Run the docker image",
                "run": " ".join(command),
            }

            job_steps.append(docker_run_step)
            job_dict = {
                "runs-on": "ubuntu-latest",
                "needs": self.get_upstream_step_names(
                    step=step, pb2_pipeline=pb2_pipeline
                ),
                "steps": job_steps,
            }
            jobs[step.name] = job_dict

        workflow_dict["jobs"] = jobs

        fileio.makedirs(self.workflow_directory)
        yaml_utils.write_yaml(workflow_path, workflow_dict, sort_keys=False)
        logger.info("Wrote GitHub workflow file to %s", workflow_path)

        if self.push:
            # Add, commit and push the pipeline workflow yaml
            self.git_repo.index.add(workflow_path)
            self.git_repo.index.commit(
                "[ZenML GitHub Actions Orchestrator] Add github workflow for "
                f"pipeline {pipeline.name}."
            )
            self.git_repo.remote().push()
            logger.info("Pushed workflow file '%s'", workflow_path)
        else:
            logger.info(
                "Automatically committing and pushing is disabled for this "
                "orchestrator. To run the pipeline, you'll have to commit and "
                "push the workflow file '%s' manually.\n"
                "If you want to update this orchestrator to automatically "
                "commit and push in the future, run "
                "`zenml orchestrator update %s --push=true`",
                workflow_path,
                self.name,
            )
