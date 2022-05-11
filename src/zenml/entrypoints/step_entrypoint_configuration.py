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
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Set

from google.protobuf import json_format
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode as Pb2PipelineNode

from zenml import constants
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.type_registry import type_registry
from zenml.integrations.registry import integration_registry
from zenml.repository import Repository
from zenml.steps import BaseStep
from zenml.steps import utils as step_utils
from zenml.utils import source_utils

DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.step_entrypoint",
]
ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"
PB2_PIPELINE_JSON_OPTION = "pb2_pipeline_json"
MAIN_MODULE_OPTION = "main_module"
STEP_SOURCE_OPTION = "step_source"
ORIGINAL_STEP_MODULE_OPTION = "original_step_module"
INPUT_SPEC_OPTION = "input_spec"


class StepEntrypointConfiguration:
    """

    Subclasses:
    custom_entrypoint_options
    setup
    post_run

    """

    def __init__(self, arguments: List[str]):
        self.entrypoint_args = self.parse_arguments(arguments)

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        This entrypoint module must execute a ZenML step when called. If
        subclasses don't overwrite this method, it will default to the
        `zenml.entrypoints.step_entrypoint` module.
        """
        return DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND

    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        """Custom options for this entrypoint configuration that are
        required in addition to the default ZenML ones.

        The options returned by this method should be strings like "my_option"
        (no "--" prefix). When the entrypoint is executed, it will parse the
        CLI arguments and expect all options to be passed in the form
        "--my_option my_value". You'll be able to retrieve the argument
        value by calling `self.entrypoint_args["my_option"]`.
        """
        return set()

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options that are required when running an entrypoint
        with this configuration.

        Subclasses should implement the `get_custom_entrypoint_options()` class
        method instead of this one if they require custom options.
        """
        zenml_default_options = {
            ENTRYPOINT_CONFIG_SOURCE_OPTION,
            PB2_PIPELINE_JSON_OPTION,
            MAIN_MODULE_OPTION,
            STEP_SOURCE_OPTION,
            ORIGINAL_STEP_MODULE_OPTION,
            INPUT_SPEC_OPTION,
        }
        return zenml_default_options.union(cls.get_custom_entrypoint_options())

    @classmethod
    def get_custom_entrypoint_arguments(cls, step: BaseStep) -> List[str]:
        """Overwrite this in subclass if it needs custom additional arguments."""
        return []

    @classmethod
    def get_entrypoint_arguments(
        cls, step: BaseStep, pb2_pipeline: Pb2Pipeline
    ) -> List[str]:
        main_module = source_utils.get_module_source_from_module(
            sys.modules["__main__"]
        )

        original_step_module = step.__module__

        if original_step_module == "__main__":
            step_module = main_module
        else:
            step_module = original_step_module

        step_source = f"{step_module}.{step.name}"

        input_spec = {
            input_name: source_utils.resolve_class(input_type)
            for input_name, input_type in step.INPUT_SPEC.items()
        }

        zenml_arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve_class(cls),
            f"--{PB2_PIPELINE_JSON_OPTION}",
            json_format.MessageToJson(pb2_pipeline),
            f"--{MAIN_MODULE_OPTION}",
            main_module,
            f"--{STEP_SOURCE_OPTION}",
            step_source,
            f"--{ORIGINAL_STEP_MODULE_OPTION}",
            original_step_module,
            f"--{INPUT_SPEC_OPTION}",
            json.dumps(input_spec),
        ]

        return zenml_arguments + cls.get_custom_entrypoint_arguments(step=step)

    @abstractmethod
    def get_run_name(self, pipeline_name: str) -> str:
        """Returns the run name.

        Subclasses must implement this and return a run name that is the same
        for all steps of this pipeline run.

        TODO: add some examples
        """

    def parse_arguments(self, arguments: List[str]) -> Dict[str, Any]:
        """Parses command line arguments.

        This method will create an `argparse.ArgumentParser` and add required
        arguments for all the options specified in the
        `get_entrypoint_options()` method of this class. Subclasses that
        require additional arguments during entrypoint execution should provide
        them by implementing the `get_custom_entrypoint_options()` class method.

        Args:
            arguments: Arguments to parse. The format should be similar to
                `sys.argv[1:]`, e.g. `["--some_option", "some_value"]`.

        Returns:
            Dictionary of the parsed arguments.
        """
        parser = argparse.ArgumentParser()

        for option_name in self.get_entrypoint_options():
            if option_name == ENTRYPOINT_CONFIG_SOURCE_OPTION:
                # This option is already used by
                # `zenml.entrypoints.step_entrypoint` to read which config
                # class to use
                continue
            parser.add_argument(f"--{option_name}", required=True)

        result, _ = parser.parse_known_args(arguments)
        return vars(result)

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
        """Does cleanup or post-processing after the step execution is finished.

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

    @staticmethod
    def _create_executor_class(
        step: BaseStep,
        original_step_module: str,
        input_spec_config: Dict[str, str],
    ) -> None:
        """Creates an executor class for a given step and adds it to the target
        module.

        Args:
            step: The step for which the executor should be created.
            original_step_module: Name of the step module when `pipeline.run()`
                was called.
            input_spec_config: The input spec config for the step. The keys
                are supposed to be the input names and the values are strings
                which will be imported and should point to
                `zenml.artifacts.BaseArtifact` subclasses.
        """
        materializers = step.get_materializers(ensure_complete=True)

        input_spec = {}
        for input_name, source in input_spec_config.items():
            artifact_class = source_utils.load_source_path_class(source)
            if not issubclass(artifact_class, BaseArtifact):
                raise TypeError(
                    f"The artifact source `{source}` passed to the entrypoint "
                    f"for the step input '{input_name}' is not pointing to a "
                    f"`{BaseArtifact}` subclass."
                )
            input_spec[input_name] = artifact_class

        output_spec = {}
        for key, value in step.OUTPUT_SIGNATURE.items():
            output_spec[key] = type_registry.get_artifact_type(value)[0]

        execution_parameters = {
            **step.PARAM_SPEC,
            **step._internal_execution_parameters,
        }

        step_utils.generate_component_class(
            step_name=step.name,
            step_module=original_step_module,
            input_spec=input_spec,
            output_spec=output_spec,
            execution_parameter_names=set(execution_parameters),
            step_function=step.entrypoint,
            materializers=materializers,
        )

    def run(self) -> None:
        """Runs the ZenML step defined by the entrypoint arguments.

        Subclasses should in most cases not need to overwrite this method and
        implement their custom logic in the `setup(...)` and `post_run(...)`
        methods instead. If you still need to customize the functionality of
        this method, make sure to still include all the existing steps as
        otherwise your step won't be executed properly.
        """
        # Make sure this entrypoint does not run an entire pipeline when
        # importing user modules. This could happen if the `pipeline.run()` call
        # is not wrapped in a function or an `if __name__== "__main__":` check)
        constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True

        # Extract and parse all the entrypoint arguments required to execute
        # the step.
        pb2_pipeline_json = self.entrypoint_args[PB2_PIPELINE_JSON_OPTION]
        pb2_pipeline = Pb2Pipeline()
        json_format.Parse(pb2_pipeline_json, pb2_pipeline)

        main_module = self.entrypoint_args[MAIN_MODULE_OPTION]
        step_source = self.entrypoint_args[STEP_SOURCE_OPTION]
        original_step_module = self.entrypoint_args[ORIGINAL_STEP_MODULE_OPTION]
        input_spec = json.loads(self.entrypoint_args[INPUT_SPEC_OPTION])

        # Do any setup that is needed before user code is imported and the step
        # is executed.
        pipeline_name = pb2_pipeline.pipeline_info.id
        _, step_name = step_source.rsplit(".", 1)
        self.setup(pipeline_name=pipeline_name, step_name=step_name)

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        # Import the main module that was executed to run the pipeline to which
        # the step getting executed belongs. Even if the step class is not
        # defined in this module, we need to import it in case the user
        # defined/imported custom materializers here.
        importlib.import_module(main_module)

        # The __main__ module when running a step inside a docker container
        # will always be the entrypoint file
        # (e.g. `zenml.entrypoints.single_step_entrypoint`). If this entrypoint
        # now needs to execute something in a different environment,
        # `sys.modules["__main__"]` would not point to the original user main
        # module anymore. That's why we set this constant here so other
        # components (e.g. step operators) can use it to correctly import it
        # in the containers they create.
        constants.USER_MAIN_MODULE = main_module

        # Create an instance of the ZenML step that this entrypoint should run.
        step_class = source_utils.load_source_path_class(step_source)
        if not issubclass(step_class, BaseStep):
            raise TypeError(
                f"The step source `{step_source}` passed to the entrypoint is "
                f"not pointing to a `{BaseStep}` subclass."
            )

        step = step_class()

        # Create the executor class that is responsible for running the step
        # function. This function call dynamically creates an executor class
        # in the `original_step_module` module which will later be used when the
        # `orchestrator.setup_and_execute_step(...)` is running the step.
        self._create_executor_class(
            step=step,
            original_step_module=original_step_module,
            input_spec_config=input_spec,
        )

        # Execute the actual step code.
        run_name = self.get_run_name(pipeline_name=pipeline_name)
        orchestrator = Repository().active_stack.orchestrator
        execution_info = orchestrator.setup_and_execute_step(
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
