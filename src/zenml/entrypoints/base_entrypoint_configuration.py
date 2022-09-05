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
"""Abstract base class for entrypoint configurations."""

import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, NoReturn, Optional, Set

from zenml.config.pipeline_configurations import PipelineDeployment
from zenml.constants import DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE
from zenml.utils import source_utils, yaml_utils

DEFAULT_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.entrypoint",
]

ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"


class BaseEntrypointConfiguration(ABC):
    """Abstract base class for entrypoint configurations that run a single step.

    If an orchestrator needs to run steps in a separate process or environment
    (e.g. a docker container), you should create a custom entrypoint
    configuration class that inherits from this class and use it to implement
    your custom entrypoint logic.

    How to subclass:
    ----------------
    There is only one mandatory method `get_run_name(...)` that you need to
    implement in order to get a functioning entrypoint. Inside this method you
    need to return a string which **has** to be the same for all steps that are
    executed as part of the same pipeline run.

    Passing additional arguments to the entrypoint:
        If you need to pass additional arguments to the entrypoint, there are
        two methods that you need to implement:
            * `get_custom_entrypoint_options()`: This method should return all
                the additional options that you require in the entrypoint.

            * `get_custom_entrypoint_arguments(...)`: This method should return
                a list of arguments that should be passed to the entrypoint.
                The arguments need to provide values for all options defined
                in the `custom_entrypoint_options()` method mentioned above.

        You'll be able to access the argument values from `self.entrypoint_args`
        inside your `StepEntrypointConfiguration` subclass.

    Running custom code inside the entrypoint:
        If you need to run custom code in the entrypoint, you can overwrite
        the `setup(...)` and `post_run(...)` methods which allow you to run
        code before and after the step execution respectively.

    How to use:
    -----------
    After you created your `StepEntrypointConfiguration` subclass, you only
    have to run the entrypoint somewhere. To do this, you should execute the
    command returned by the `get_entrypoint_command()` method with the
    arguments returned by the `get_entrypoint_arguments(...)` method.

    Example:
    ```python
    class MyStepEntrypointConfiguration(StepEntrypointConfiguration):
        ...

    class MyOrchestrator(BaseOrchestrator):
        def prepare_or_run_pipeline(
            self,
            sorted_list_of_steps: List[BaseStep],
            pipeline: "BasePipeline",
            pb2_pipeline: Pb2Pipeline,
            stack: "Stack",
            runtime_configuration: "RuntimeConfiguration",
        ) -> Any:
            ...

            cmd = MyStepEntrypointConfiguration.get_entrypoint_command()
            for step in sorted_list_of_steps:
                ...

                args = MyStepEntrypointConfiguration.get_entrypoint_arguments(
                    step=step, pb2_pipeline=pb2_pipeline
                )
                # Run the command and pass it the arguments. Our example
                # orchestrator here executes the entrypoint in a separate
                # process, but in a real-world scenario you would probably run
                # it inside a docker container or a different environment.
                import subprocess
                subprocess.check_call(cmd + args)

    Attributes:
        entrypoint_args: The parsed arguments passed to the entrypoint.
    ```
    """

    def __init__(self, arguments: List[str]):
        """Initializes the entrypoint configuration.

        Args:
            arguments: Command line arguments to configure this object.
        """
        self.entrypoint_args = self._parse_arguments(arguments)

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        This entrypoint module must execute a ZenML step when called. If
        subclasses don't overwrite this method, it will default to running the
        `zenml.entrypoints.step_entrypoint` module.

        **Note**: This command won't work on its own but needs to be called with
            the arguments returned by the `get_entrypoint_arguments(...)`
            method of this class.

        Returns:
            A list of strings with the command.
        """
        return DEFAULT_ENTRYPOINT_COMMAND

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            A set of strings with all required options.
        """
        return {
            # Importable source pointing to the entrypoint configuration class
            # that should be used inside the entrypoint.
            ENTRYPOINT_CONFIG_SOURCE_OPTION,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        The argument list should be something that
        `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
        `["--some_option", "some_value"]` or `["--some_option=some_value"]`).
        It needs to provide values for all options returned by the
        `get_entrypoint_options()` method of this class.

        **Note**: Subclasses should implement the
            `get_custom_entrypoint_arguments(...)` class method instead of
            this one if they require custom arguments.

        Args:
            **kwargs: Kwargs to be used in subclasses.

        Returns:
            A list of strings with the arguments.
        """
        arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve_class(cls),
        ]

        return arguments

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the run name.

        Subclasses must implement this and return a run name that is the same
        for all steps of this pipeline run.

        Examples:
        * If you're in an orchestrator environment which has an equivalent
            concept to a pipeline run, you can use that as the run name. E.g.
            Kubeflow Pipelines sets a run id as environment variable in all
            pods which we can reuse: `return os.environ["KFP_RUN_ID"]`
        * If that isn't possible, you could pass a unique value as an argument
            to the entrypoint (make sure to also return it from
            `get_custom_entrypoint_options()`) and use it like this:
            `return self.entrypoint_args["run_name_option"]`

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The run name.
        """
        return None

    @classmethod
    def _parse_arguments(cls, arguments: List[str]) -> Dict[str, Any]:
        """Parses command line arguments.

        This method will create an `argparse.ArgumentParser` and add required
        arguments for all the options specified in the
        `get_entrypoint_options()` method of this class. Subclasses that
        require additional arguments during entrypoint execution should provide
        them by implementing the `get_custom_entrypoint_options()` class method.

        Args:
            arguments: Arguments to parse. The format should be something that
                `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
                `["--some_option", "some_value"]` or
                `["--some_option=some_value"]`).

        Returns:
            Dictionary of the parsed arguments.

        # noqa: DAR402
        Raises:
            ValueError: If the arguments are not valid.
        """
        # Argument parser subclass that suppresses some argparse logs and
        # raises an exception instead of the `sys.exit()` call
        class _CustomParser(argparse.ArgumentParser):
            def error(self, message: str) -> NoReturn:
                raise ValueError(
                    f"Failed to parse entrypoint arguments: {message}"
                )

        parser = _CustomParser()

        for option_name in cls.get_entrypoint_options():
            if option_name == ENTRYPOINT_CONFIG_SOURCE_OPTION:
                # This option is already used by
                # `zenml.entrypoints.step_entrypoint` to read which config
                # class to use
                continue
            parser.add_argument(f"--{option_name}", required=True)

        result, _ = parser.parse_known_args(arguments)
        return vars(result)

    def load_deployment_config(self) -> "PipelineDeployment":
        """Loads the deployment config.

        If a subclass implements the `get_run_name` method and returns a
        value from it, this method will also update the run name of the
        deployment config.

        Returns:
            The (updated) deployment config.
        """
        config_dict = yaml_utils.read_yaml(DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE)
        deployment_config = PipelineDeployment.parse_obj(config_dict)

        custom_run_name = self.get_run_name(
            pipeline_name=deployment_config.pipeline.name
        )
        if custom_run_name:
            deployment_config = deployment_config.copy(
                update={"run_name": custom_run_name}
            )

        return deployment_config

    @abstractmethod
    def run(self) -> None:
        """Runs a single ZenML step.

        Subclasses should in most cases not need to overwrite this method and
        implement their custom logic in the `setup(...)` and `post_run(...)`
        methods instead. If you still need to customize the functionality of
        this method, make sure to still include all the existing logic as your
        step won't be executed properly otherwise.

        Raises:
            TypeError: If the arguments passed to the entrypoint are invalid.
        """
