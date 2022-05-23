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
import argparse
import importlib
import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, NoReturn, Optional, Set, Type

from google.protobuf import json_format
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode as Pb2PipelineNode

from zenml import constants
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.type_registry import type_registry
from zenml.integrations.registry import integration_registry
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.repository import Repository
from zenml.steps import BaseStep
from zenml.steps import utils as step_utils
from zenml.utils import source_utils

DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.step_entrypoint",
]
# Constants for all the ZenML default entrypoint options
ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"
PIPELINE_JSON_OPTION = "pipeline_json"
MAIN_MODULE_SOURCE_OPTION = "main_module_source"
STEP_SOURCE_OPTION = "step_source"
INPUT_ARTIFACT_SOURCES_OPTION = "input_artifact_sources"
MATERIALIZER_SOURCES_OPTION = "materializer_sources"


class StepEntrypointConfiguration(ABC):
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
    ```
    """

    def __init__(self, arguments: List[str]):
        """Initializes the entrypoint configuration.

        Args:
            arguments: Command line arguments to configure this object.
        """
        self.entrypoint_args = self._parse_arguments(arguments)

    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        """Custom options for this entrypoint configuration that are
        required in addition to the default ZenML ones.

        The options returned by this method should be strings like "my_option"
        (no "--" prefix). When the entrypoint is executed, it will parse the
        command line arguments and expect all options to be passed in the form
        "--my_option my_value". You'll be able to retrieve the argument
        value by calling `self.entrypoint_args["my_option"]`.
        """
        return set()

    @classmethod
    def get_custom_entrypoint_arguments(
        cls, step: BaseStep, **kwargs: Any
    ) -> List[str]:
        """Custom arguments that the entrypoint command should be called with.

        The argument list should be something that
        `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
        `["--some_option", "some_value"]` or `["--some_option=some_value"]`).
        It needs to provide values for all options returned by the
        `get_custom_entrypoint_options()` method of this class.

        Args:
            step: The step that the entrypoint should run using the arguments
                returned by this method.
        """
        return []

    @abstractmethod
    def get_run_name(self, pipeline_name: str) -> str:
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
        """

    def setup(self, pipeline_name: str, step_name: str) -> None:
        """Runs setup code that needs to run before any user code is imported
        or the step is executed.

        Subclasses should overwrite this method if they need to perform any
        additional setup, but should in most cases include a
        `super().setup(...)` call so the ZenML setup code will still be
        executed.

        Args:
            pipeline_name: Name of the parent pipeline of the step that will
                be executed.
            step_name: Name of the step that will be executed.
        """
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.getLogger().setLevel(logging.INFO)

    def post_run(
        self,
        pipeline_name: str,
        step_name: str,
        pipeline_node: Pb2PipelineNode,
        execution_info: Optional[data_types.ExecutionInfo] = None,
    ) -> None:
        """Does cleanup or post-processing after the step finished running.

        Subclasses should overwrite this method if they need to run any
        additional code after the step execution.

        Args:
            pipeline_name: Name of the parent pipeline of the step that was
                executed.
            step_name: Name of the step that was executed.
            pipeline_node: Protobuf node corresponding to the step that was
                executed.
            execution_info: Info about the finished step execution.
        """

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        This entrypoint module must execute a ZenML step when called. If
        subclasses don't overwrite this method, it will default to running the
        `zenml.entrypoints.step_entrypoint` module.

        **Note**: This command won't work on its own but needs to be called with
            the arguments returned by the `get_entrypoint_arguments(...)`
            method of this class.
        """
        return DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options that are required when running an entrypoint
        with this configuration.

        **Note**: Subclasses should implement the
            `get_custom_entrypoint_options()` class method instead of this
            one if they require custom options.
        """
        zenml_options = {
            # Importable source pointing to the entrypoint configuration class
            # that should be used inside the entrypoint.
            ENTRYPOINT_CONFIG_SOURCE_OPTION,
            # Json representation of the parent pipeline of the step that
            # will be executed. This is needed in order to create the tfx
            # launcher in the entrypoint that will run the ZenML step.
            PIPELINE_JSON_OPTION,
            # Importable source pointing to the python module that was executed
            # to run a pipeline. This will be imported inside the entrypoint to
            # make sure all custom materializer/artifact types are registered.
            MAIN_MODULE_SOURCE_OPTION,
            # Importable source pointing to the ZenML step class that should be
            # run inside the entrypoint. This will be used to recreate the tfx
            # executor class that is required to run the step function.
            STEP_SOURCE_OPTION,
            # Dictionary mapping the step input names to importable sources
            # pointing to `zenml.artifacts.base_artifact.BaseArtifact`
            # subclasses. These classes are needed to recreate the tfx executor
            # class and can't be inferred as we do not have access to the
            # output artifacts from previous steps.
            INPUT_ARTIFACT_SOURCES_OPTION,
            # Dictionary mapping the step output names to importable sources
            # pointing to
            # `zenml.materializers.base_materializer.BaseMaterializer`
            # subclasses. These classes are needed to recreate the tfx executor
            # class if custom materializers were specified for the step.
            MATERIALIZER_SOURCES_OPTION,
        }
        custom_options = cls.get_custom_entrypoint_options()
        return zenml_options.union(custom_options)

    @classmethod
    def get_entrypoint_arguments(
        cls,
        step: BaseStep,
        pb2_pipeline: Pb2Pipeline,
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
            step: The step that the entrypoint should run using the arguments
                returned by this method.
            pb2_pipeline: The protobuf representation of the pipeline to which
                the `step` belongs.
            **kwargs: Custom options that will be passed to
                `get_custom_entrypoint_arguments()`.

        Raises:
            ValueError: If the argument format is incorrect or one of the
                options is missing.
        """
        # Get an importable source of the user main module. If the `__main__`
        # module is not the actual module that a user executed (e.g. if we're
        # in some docker container entrypoint) use the ZenML constant that
        # points to the actual user main module. If not resolve the `__main__`
        # module to something that can be imported during entrypoint execution.
        main_module_source = (
            constants.USER_MAIN_MODULE
            or source_utils.get_module_source_from_module(
                sys.modules["__main__"]
            )
        )

        # TODO [ENG-887]: Move this method to source utils
        def _resolve_class(class_: Type[Any]) -> str:
            """Resolves the input class in a way that it is importable inside
            the entrypoint.
            """
            source = source_utils.resolve_class(class_)
            module_source, class_source = source.rsplit(".", 1)
            if module_source == "__main__":
                # If the class is defined inside the `__main__` module it will
                # not be importable in the entrypoint (The `__main__` module
                # there will be the actual entrypoint module). We therefore
                # replace the module source by the importable main module
                # source computed above.
                module_source = main_module_source

            return f"{module_source}.{class_source}"

        # Resolve the step class
        step_source = _resolve_class(step.__class__)

        # Resolve the input artifact classes
        input_artifact_sources = {
            input_name: _resolve_class(input_type)
            for input_name, input_type in step.INPUT_SPEC.items()
        }

        # Resolve the output materializer classes
        materializer_classes = step.get_materializers(ensure_complete=True)
        materializer_sources = {
            output_name: _resolve_class(materializer_class)
            for output_name, materializer_class in materializer_classes.items()
        }

        # See `get_entrypoint_options()` for an in -depth explanation of all
        # these arguments.
        zenml_arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve_class(cls),
            f"--{PIPELINE_JSON_OPTION}",
            json_format.MessageToJson(pb2_pipeline),
            f"--{MAIN_MODULE_SOURCE_OPTION}",
            main_module_source,
            f"--{STEP_SOURCE_OPTION}",
            step_source,
            f"--{INPUT_ARTIFACT_SOURCES_OPTION}",
            json.dumps(input_artifact_sources),
            f"--{MATERIALIZER_SOURCES_OPTION}",
            json.dumps(materializer_sources),
        ]

        custom_arguments = cls.get_custom_entrypoint_arguments(
            step=step, **kwargs
        )
        all_arguments = zenml_arguments + custom_arguments

        # Try to parse the arguments here to validate the format and that
        # values for all options are provided.
        cls._parse_arguments(all_arguments)

        return all_arguments

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

        Raises:
            ValueError: If the parsing failed because the argument format is
                incorrect or one of the options is missing.
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

    @staticmethod
    def _create_executor_class(
        step: BaseStep,
        input_artifact_sources: Dict[str, str],
        materializer_sources: Dict[str, str],
    ) -> None:
        """Creates an executor class for the given step.

        Args:
            step: The step for which the executor class should be created.
            input_artifact_sources: Dictionary mapping step input names to a
                source strings of the artifact class to use for that input.
            materializer_sources: Dictionary mapping step output names to a
                source string of the materializer class to use for that output.
        """
        # Import the input artifact classes from the given sources
        input_spec = {}
        for input_name, source in input_artifact_sources.items():
            artifact_class = source_utils.load_source_path_class(source)
            if not issubclass(artifact_class, BaseArtifact):
                raise TypeError(
                    f"The artifact source `{source}` passed to the entrypoint "
                    f"for the step input '{input_name}' is not pointing to a "
                    f"`{BaseArtifact}` subclass."
                )
            input_spec[input_name] = artifact_class

        output_spec = {
            key: type_registry.get_artifact_type(value)[0]
            for key, value in step.OUTPUT_SIGNATURE.items()
        }

        execution_parameters = {
            **step.PARAM_SPEC,
            **step._internal_execution_parameters,
        }

        materializers = {}
        for output_name, source in materializer_sources.items():
            materializer_class = source_utils.load_source_path_class(source)
            if not issubclass(materializer_class, BaseMaterializer):
                raise TypeError(
                    f"The materializer source `{source}` passed to the "
                    f"entrypoint for the step output '{output_name}' is not "
                    f"pointing to a `{BaseMaterializer}` subclass."
                )
            materializers[output_name] = materializer_class

        step_utils.generate_component_class(
            step_name=step.name,
            step_module=step.__module__,
            input_spec=input_spec,
            output_spec=output_spec,
            execution_parameter_names=set(execution_parameters),
            step_function=step.entrypoint,
            materializers=materializers,
        )

    def run(self) -> None:
        """Runs a single ZenML step.

        Subclasses should in most cases not need to overwrite this method and
        implement their custom logic in the `setup(...)` and `post_run(...)`
        methods instead. If you still need to customize the functionality of
        this method, make sure to still include all the existing logic as your
        step won't be executed properly otherwise.
        """
        # Make sure this entrypoint does not run an entire pipeline when
        # importing user modules. This could happen if the `pipeline.run()` call
        # is not wrapped in a function or an `if __name__== "__main__":` check)
        constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True

        # Extract and parse all the entrypoint arguments required to execute
        # the step. See `get_entrypoint_options()` for an in-depth explanation
        # of all these arguments.
        pb2_pipeline_json = self.entrypoint_args[PIPELINE_JSON_OPTION]
        pb2_pipeline = Pb2Pipeline()
        json_format.Parse(pb2_pipeline_json, pb2_pipeline)

        main_module_source = self.entrypoint_args[MAIN_MODULE_SOURCE_OPTION]
        step_source = self.entrypoint_args[STEP_SOURCE_OPTION]
        input_artifact_sources = json.loads(
            self.entrypoint_args[INPUT_ARTIFACT_SOURCES_OPTION]
        )
        materializer_sources = json.loads(
            self.entrypoint_args[MATERIALIZER_SOURCES_OPTION]
        )

        # Get some common values that will be used throughout the remainder of
        # this method
        pipeline_name = pb2_pipeline.pipeline_info.id
        if "@" in step_source:
            # Get rid of potential ZenML version pins if the source looks like
            # this `zenml.some_module.SomeClass@zenml_0.9.9`
            step_source, _ = step_source.split("@", 1)
        step_module, step_name = step_source.rsplit(".", 1)

        # Allow subclasses to run custom code before user code is imported and
        # the step is executed.
        self.setup(pipeline_name=pipeline_name, step_name=step_name)

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        # Import the main module that was executed to run the pipeline to which
        # the step getting executed belongs. Even if the step class is not
        # defined in this module, we need to import it in case the user
        # defined/imported custom materializers/artifacts here that ZenML needs
        # to execute the step.
        importlib.import_module(main_module_source)

        # The `__main__` module when running a step inside a docker container
        # will always be the entrypoint file
        # (e.g. `zenml.entrypoints.single_step_entrypoint`). If this entrypoint
        # now needs to execute something in a different environment,
        # `sys.modules["__main__"]` would not point to the original user main
        # module anymore. That's why we set this constant here so other
        # components (e.g. step operators) can use it to correctly import it
        # in the containers they create.
        constants.USER_MAIN_MODULE = main_module_source

        # Create an instance of the ZenML step that this entrypoint should run.
        step_class = source_utils.load_source_path_class(step_source)
        if not issubclass(step_class, BaseStep):
            raise TypeError(
                f"The step source `{step_source}` passed to the "
                f"entrypoint is not pointing to a `{BaseStep}` subclass."
            )

        step = step_class()

        # Compute the name of the module in which the step was in when the
        # pipeline run was started. This could potentially differ from the
        # module part of `STEP_SOURCE_OPTION` if the step was defined in
        # the `__main__` module (e.g. the step was defined in `run.py` and the
        # pipeline run was started by the call `python run.py`).
        # Why we need this: The executor source is stored inside the protobuf
        # pipeline representation object `pb2_pipeline` which was passed to
        # this entrypoint. Tfx will try to load the executor class from that
        # source, so we need to recreate the executor class in the same module.
        original_step_module = (
            "__main__" if step_module == main_module_source else step_module
        )

        # Make sure the `__module__` attribute of our step instance points to
        # this original module so the executor class gets created in the
        # correct module.
        step.__module__ = original_step_module

        # Create the executor class that is responsible for running the step
        # function. This method call dynamically creates an executor class
        # which will later be used when `orchestrator.run_step(...)` is running
        # the step.
        self._create_executor_class(
            step=step,
            input_artifact_sources=input_artifact_sources,
            materializer_sources=materializer_sources,
        )

        # Execute the actual step code.
        run_name = self.get_run_name(pipeline_name=pipeline_name)
        orchestrator = Repository().active_stack.orchestrator
        execution_info = orchestrator.run_step(
            step=step, run_name=run_name, pb2_pipeline=pb2_pipeline
        )

        # Allow subclasses to run custom code after the step finished executing.
        pipeline_node = orchestrator._get_node_with_step_name(
            step_name=step_name, pb2_pipeline=pb2_pipeline
        )
        self.post_run(
            pipeline_name=pipeline_name,
            step_name=step_name,
            pipeline_node=pipeline_node,
            execution_info=execution_info,
        )
