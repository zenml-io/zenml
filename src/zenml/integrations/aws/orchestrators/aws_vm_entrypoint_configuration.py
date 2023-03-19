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
"""GCP VM orchestrator definition."""

import importlib
import json
import sys
from typing import Any, List, Set, Type

from google.protobuf import json_format
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml import constants
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.integrations.registry import integration_registry
from zenml.repository import Repository
from zenml.steps import BaseStep
from zenml.utils import source_utils, string_utils, yaml_utils

DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.step_entrypoint",
]
# Constants for all the ZenML default entrypoint options
ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"
MAIN_MODULE_SOURCE_OPTION = "main_module_source"
SOURCES_DICT = "sources_dict"
DEFAULT_SINGLE_STEP_CONTAINER_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.step_entrypoint",
]

RUN_NAME_OPTION = "run_name"
PB2_PIPELINE_JSON_FILE_PATH = "pb2_pipeline_json_file_path"


class AWSVMEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint for AWS VM orchestrators."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running an entrypoint with this configuration.

        **Note**: Subclasses should implement the
            `get_custom_entrypoint_options()` class method instead of this
            one if they require custom options.

        Returns:
            A set of strings with all required options.
        """
        zenml_options = {
            # Importable source pointing to the entrypoint configuration class
            # that should be used inside the entrypoint.
            ENTRYPOINT_CONFIG_SOURCE_OPTION,
            # Importable source pointing to the python module that was executed
            # to run a pipeline. This will be imported inside the entrypoint to
            # make sure all custom materializer/artifact types are registered.
            MAIN_MODULE_SOURCE_OPTION,
            # The following dict is a collection of these options:
            # 1. Importable source pointing to the ZenML step class that should be
            # run inside the entrypoint. This will be used to recreate the tfx
            # executor class that is required to run the step function.
            # 2. Base64 encoded json dictionary mapping the step input names to
            # importable sources pointing to
            # `zenml.artifacts.base_artifact.BaseArtifact` subclasses.
            # These classes are needed to recreate the tfx executor
            # class and can't be inferred as we do not have access to the
            # output artifacts from previous steps.
            # 3. Base64 encoded json dictionary mapping the step output names to
            # importable sources pointing to
            # `zenml.materializers.base_materializer.BaseMaterializer`
            # subclasses. These classes are needed to recreate the tfx executor
            # class if custom materializers were specified for the step.
            SOURCES_DICT,
        }
        custom_options = cls.get_custom_entrypoint_options()
        return zenml_options.union(custom_options)

    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        """Get custom entrypoint options.

        Returns:
            A set of custom options.
        """
        return {RUN_NAME_OPTION, PB2_PIPELINE_JSON_FILE_PATH}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        steps: List[BaseStep],
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
            steps: The list of steps that the entrypoint should run using the arguments
                returned by this method.
            pb2_pipeline: The protobuf representation of the pipeline to which
                the `step` belongs.
            **kwargs: Custom options that will be passed to
                `get_custom_entrypoint_arguments()`.

        Returns:
            A list of strings with the arguments.
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

        def _resolve_class(class_: Type[Any]) -> str:
            """Resolves the input class so it is importable inside the entrypoint.

            Args:
                class_: The class to resolve.

            Returns:
                The importable source of the class.
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

        # Resolve the entrypoint config source
        entrypoint_config_source = _resolve_class(cls)

        sources_dict = {}
        for step in steps:
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
            # Put it all in one dict to pass to the entrypoint
            sources_dict[step.name] = (
                step_source,
                materializer_sources,
                input_artifact_sources,
            )

        # See `get_entrypoint_options()` for an in -depth explanation of all
        # these arguments.
        zenml_arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            entrypoint_config_source,
            f"--{MAIN_MODULE_SOURCE_OPTION}",
            main_module_source,
            f"--{SOURCES_DICT}",
            # Base64 encode the json strings to make sure there are no issues
            # when passing these arguments
            string_utils.b64_encode(json.dumps(sources_dict)),
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
    def get_custom_entrypoint_arguments(
        cls, step: BaseStep, *args: Any, **kwargs: Any
    ) -> List[str]:
        """Get custom entrypoint arguments.

        Args:
            step: A ZenML step.
            *args: Free arguments.
            **kwargs: Free named arguments.

        Returns:
            List of custom entrypoint arguments.
        """
        return [
            f"--{RUN_NAME_OPTION}",
            kwargs[RUN_NAME_OPTION],
            f"--{PB2_PIPELINE_JSON_FILE_PATH}",
            kwargs[PB2_PIPELINE_JSON_FILE_PATH],
        ]

    def get_run_name(self, pipeline_name: str) -> str:
        """Returns the run name.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            The run name.
        """
        return self.entrypoint_args[RUN_NAME_OPTION]

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
        # Make sure this entrypoint does not run an entire pipeline when
        # importing user modules. This could happen if the `pipeline.run()` call
        # is not wrapped in a function or an `if __name__== "__main__":` check)
        constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True

        # We do this here to make fileio work
        orchestrator = Repository().active_stack.orchestrator

        # Extract and parse all the entrypoint arguments required to execute
        # the step. See `get_entrypoint_options()` for an in-depth explanation
        # of all these arguments.
        pb2_pipeline = Pb2Pipeline()
        pb2_pipeline_json = yaml_utils.read_json_string(
            self.entrypoint_args[PB2_PIPELINE_JSON_FILE_PATH]
        )
        json_format.Parse(pb2_pipeline_json, pb2_pipeline)

        main_module_source = self.entrypoint_args[MAIN_MODULE_SOURCE_OPTION]
        sources_dict = json.loads(
            string_utils.b64_decode(self.entrypoint_args[SOURCES_DICT])
        )

        # Get some common values that will be used throughout the remainder of
        # this method
        pipeline_name = pb2_pipeline.pipeline_info.id

        # Allow subclasses to run custom code before user code is imported and
        # the step is executed.
        self.setup(pipeline_name=pipeline_name, step_name=None)

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

        run_name = self.get_run_name(pipeline_name=pipeline_name)

        for step_name, (
            step_source,
            materializer_sources,
            input_artifact_sources,
        ) in sources_dict.items():
            # Get rid of potential ZenML version pins if the source looks like
            # this `zenml.some_module.SomeClass@zenml_0.9.9`
            if "@" in step_source:
                step_source, _ = step_source.split("@", 1)
            step_module, step_name = step_source.rsplit(".", 1)

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
                "__main__"
                if step_module == main_module_source
                else step_module
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
