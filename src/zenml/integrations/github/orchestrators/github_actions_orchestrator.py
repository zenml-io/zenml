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
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast

from git.exc import InvalidGitRepositoryError
from git.repo.base import Repo

from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.container_registries import (
    BaseContainerRegistry,
    GitHubContainerRegistryFlavor,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.github.flavors.github_actions_orchestrator_flavor import (
    GitHubActionsOrchestratorConfig,
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
from zenml.utils import yaml_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment

from zenml.enums import StackComponentType
from zenml.stack import StackValidator

logger = get_logger(__name__)

# Git remote URL prefixes that indicate a GitHub repository.
GITHUB_REMOTE_URL_PREFIXES = ["git@github.com", "https://github.com"]
# Name of the GitHub Action used to login to docker
DOCKER_LOGIN_ACTION = "docker/login-action@v1"

ENV_ZENML_GH_ACTIONS_RUN_ID = "ZENML_GH_ACTIONS_RUN_ID"


class GitHubActionsOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using GitHub Actions."""

    _git_repo: Optional[Repo] = None

    @property
    def config(self) -> GitHubActionsOrchestratorConfig:
        """Returns the `GitHubActionsOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(GitHubActionsOrchestratorConfig, self._config)

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
            if not (is_github_repo or self.config.skip_github_repository_check):
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

            if container_registry.config.is_local:
                return False, (
                    "The GitHub Actions orchestrator requires a remote "
                    f"container registry, but the '{container_registry.name}' "
                    "container registry of your active stack points to a local "
                    f"URI '{container_registry.config.uri}'. Please make sure "
                    "stacks with a GitHub Actions orchestrator always contain "
                    "remote container registries."
                )

            if container_registry.requires_authentication:
                return False, (
                    "The GitHub Actions orchestrator currently only works with "
                    "GitHub container registries or public container "
                    f"registries, but your {container_registry.flavor} "
                    f"container registry '{container_registry.name}' requires "
                    "authentication."
                )

            for component in stack.components.values():
                if component.local_path is not None:
                    return False, (
                        "The GitHub Actions orchestrator runs pipelines on "
                        "remote GitHub Actions runners, but the "
                        f"'{component.name}' {component.type.value} of your "
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
            isinstance(container_registry, GitHubContainerRegistryFlavor)
            and container_registry.config.automatic_token_authentication
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
    ) -> Dict[str, Any]:
        """GitHub Actions step for writing required environment variables.

        Args:
            file_name: Name of the environment file that should be written.
            secrets_manager: Secrets manager that will be used to read secrets
                during pipeline execution.

        Returns:
            Dictionary specifying the GitHub Actions step for writing the
            environment file.
        """
        # Always include the environment variable that specifies whether
        # we're running in a GitHub Action workflow so the secret manager knows
        # how to query secret values
        command = (
            f'echo {ENV_IN_GITHUB_ACTIONS}="${ENV_IN_GITHUB_ACTIONS}" '
            f"> {file_name}; "
        )

        run_id_placeholder = (
            "${{ github.run_id }}_${{ github.run_number }}_"
            "${{ github.run_attempt }}"
        )
        command += (
            f'echo {ENV_ZENML_GH_ACTIONS_RUN_ID}="{run_id_placeholder}" '
            f">> {file_name}; "
        )

        if isinstance(secrets_manager, GitHubSecretsManager):
            # Write all ZenML secrets into the environment file. Explicitly writing
            # these `${{ secrets.<SECRET_NAME> }}` placeholders into the workflow
            # yaml is the only way for us to access the GitHub secrets in a GitHub
            # Actions workflow.
            append_secret_placeholder = "echo {secret_name}=${{{{ secrets.{secret_name} }}}} >> {file}; "
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

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_GH_ACTIONS_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_GH_ACTIONS_RUN_ID}."
            )

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.

        Raises:
            RuntimeError: If the orchestrator should only run in a clean git
                repository and the repository is dirty.
        """
        if (
            not self.config.skip_dirty_repository_check
            and self.git_repo.is_dirty(untracked_files=True)
        ):
            raise RuntimeError(
                "Trying to run a pipeline from within a dirty (=containing "
                "untracked/uncommitted files) git repository."
                "If you want this orchestrator to skip the dirty repo check in "
                f"the future, run\n `zenml orchestrator update {self.name} "
                "--skip_dirty_repository_check=true`"
            )

        docker_image_builder = PipelineDockerImageBuilder()
        repo_digest = docker_image_builder.build_and_push_docker_image(
            deployment=deployment, stack=stack
        )
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """Writes a GitHub Action workflow yaml and optionally pushes it.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.

        Raises:
            ValueError: If a schedule without a cron expression or with an
                invalid cron expression is passed.
        """
        schedule = deployment.schedule

        workflow_name = deployment.pipeline.name
        if schedule:
            # Add a suffix to the workflow filename so we don't overwrite
            # scheduled pipeline by future schedules or single pipeline runs.
            datetime_string = datetime.utcnow().strftime("%y_%m_%d_%H_%M_%S")
            workflow_name += f"-scheduled-{datetime_string}"

        workflow_path = os.path.join(
            self.workflow_directory,
            f"{workflow_name}.yaml",
        )

        workflow_dict: Dict[str, Any] = {
            "name": workflow_name,
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

        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]

        # Prepare the step that writes an environment file which will get
        # passed to the docker image
        env_file_name = ".zenml_docker_env"
        write_env_file_step = self._write_environment_file_step(
            file_name=env_file_name, secrets_manager=stack.secrets_manager
        )
        docker_run_args = ["--env-file", env_file_name]

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
        ] + StepEntrypointConfiguration.get_entrypoint_command()

        jobs = {}
        for step_name, step in deployment.steps.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the "
                    "GitHub Actions orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step.config.name,
                )

            job_steps = []

            # Copy the shared dicts here to avoid creating yaml anchors (which
            # are currently not supported in GitHub workflow yaml files)
            job_steps.append(copy.deepcopy(write_env_file_step))

            if docker_login_step:
                job_steps.append(copy.deepcopy(docker_login_step))

            entrypoint_args = (
                StepEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name,
                )
            )

            command = base_command + entrypoint_args
            docker_run_step = {
                "name": "Run the docker image",
                "run": " ".join(command),
            }

            job_steps.append(docker_run_step)
            job_dict = {
                "runs-on": "ubuntu-latest",
                "needs": step.spec.upstream_steps,
                "steps": job_steps,
            }
            jobs[step.config.name] = job_dict

        workflow_dict["jobs"] = jobs

        fileio.makedirs(self.workflow_directory)
        yaml_utils.write_yaml(workflow_path, workflow_dict, sort_keys=False)
        logger.info("Wrote GitHub workflow file to %s", workflow_path)

        if self.config.push:
            # Add, commit and push the pipeline workflow yaml
            self.git_repo.index.add(workflow_path)
            self.git_repo.index.commit(
                "[ZenML GitHub Actions Orchestrator] Add github workflow for "
                f"pipeline {deployment.pipeline.name}."
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
