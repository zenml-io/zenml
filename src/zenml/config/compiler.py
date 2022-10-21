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
"""Class for compiling ZenML pipelines into a serializable format."""
import copy
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Sequence, Tuple

import tfx.orchestration.pipeline as tfx_pipeline
from google.protobuf import json_format
from tfx.dsl.compiler.compiler import Compiler as TFXCompiler
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.config.pipeline_configurations import PipelineRunConfiguration
from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.config.settings_resolver import SettingsResolver
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.exceptions import PipelineInterfaceError, StackValidationError
from zenml.utils import source_utils, string_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.steps import BaseStep
    from zenml.stack import Stack

from zenml.logger import get_logger

logger = get_logger(__file__)


class Compiler:
    """Compiles ZenML pipelines to serializable representations."""

    def compile(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        run_configuration: PipelineRunConfiguration,
    ) -> PipelineDeployment:
        """Compiles a ZenML pipeline to a serializable representation.

        Args:
            pipeline: The pipeline to compile.
            stack: The stack on which the pipeline will run.
            run_configuration: The run configuration for this pipeline.

        Returns:
            The compiled pipeline.
        """
        logger.debug("Compiling pipeline `%s`.", pipeline.name)
        # Copy the pipeline before we apply any run-level configurations so
        # we don't mess with the pipeline object/step objects in any way
        pipeline = copy.deepcopy(pipeline)
        self._apply_run_configuration(
            pipeline=pipeline, config=run_configuration
        )
        self._verify_distinct_step_names(pipeline=pipeline)

        pipeline.connect(**pipeline.steps)
        pb2_pipeline = self._compile_proto_pipeline(
            pipeline=pipeline, stack=stack
        )

        pipeline_settings = self._filter_and_validate_settings(
            settings=pipeline.configuration.settings,
            configuration_level=ConfigurationLevel.PIPELINE,
            stack=stack,
        )
        pipeline.configure(settings=pipeline_settings, merge=False)

        settings_to_passdown = {
            key: settings
            for key, settings in pipeline_settings.items()
            if ConfigurationLevel.STEP in settings.LEVEL
        }

        steps = {
            name: self._compile_step(
                step=step,
                pipeline_settings=settings_to_passdown,
                pipeline_extra=pipeline.configuration.extra,
                stack=stack,
            )
            for name, step in self._get_sorted_steps(
                pb2_pipeline, steps=pipeline.steps
            )
        }

        self._ensure_required_stack_components_exist(
            stack=stack, steps=list(steps.values())
        )

        run_name = run_configuration.run_name or self._get_default_run_name(
            pipeline_name=pipeline.name
        )

        encoded_pb2_pipeline = string_utils.b64_encode(
            json_format.MessageToJson(pb2_pipeline)
        )

        deployment = PipelineDeployment(
            run_name=run_name,
            stack_id=stack.id,
            schedule=run_configuration.schedule,
            pipeline=pipeline.configuration,
            proto_pipeline=encoded_pb2_pipeline,
            steps=steps,
        )
        logger.debug("Compiled pipeline deployment: %s", deployment)
        return deployment

    def _apply_run_configuration(
        self, pipeline: "BasePipeline", config: PipelineRunConfiguration
    ) -> None:
        """Applies run configurations to the pipeline and its steps.

        Args:
            pipeline: The pipeline to configure.
            config: The run configurations.

        Raises:
            KeyError: If the run configuration contains options for a
                non-existent step.
        """
        pipeline.configure(
            enable_cache=config.enable_cache,
            settings=config.settings,
            extra=config.extra,
        )

        for step_name, step_config in config.steps.items():
            if step_name not in pipeline.steps:
                raise KeyError(f"No step with name {step_name}.")
            pipeline.steps[step_name]._apply_configuration(step_config)

    def _verify_distinct_step_names(self, pipeline: "BasePipeline") -> None:
        """Verifies that all steps inside the pipeline have separate names.

        Args:
            pipeline: The pipeline to verify.

        Raises:
            PipelineInterfaceError: If multiple steps share the same name.
        """
        step_names: Dict[str, str] = {}

        for step_argument_name, step in pipeline.steps.items():
            previous_argument_name = step_names.get(step.name, None)
            if previous_argument_name:
                raise PipelineInterfaceError(
                    f"Found multiple step objects with the same name "
                    f"`{step.name}` for arguments '{previous_argument_name}' "
                    f"and '{step_argument_name}' in pipeline "
                    f"'{pipeline.name}'. All steps of a ZenML pipeline need "
                    "to have distinct names. To solve this issue, assign a new "
                    "name to one of the steps by calling "
                    "`my_step_instance.configure(name='some_distinct_name')`"
                )

            step_names[step.name] = step_argument_name

    def _filter_and_validate_settings(
        self,
        settings: Dict[str, "BaseSettings"],
        configuration_level: ConfigurationLevel,
        stack: "Stack",
    ) -> Dict[str, "BaseSettings"]:
        """Filters and validates settings.

        Args:
            settings: The settings to check.
            configuration_level: The level on which these settings
                were configured.
            stack: The stack on which the pipeline will run.

        Raises:
            TypeError: If settings with an unsupported configuration
                level were specified.

        Returns:
            The filtered settings.
        """
        validated_settings = {}

        for key, settings_instance in settings.items():
            resolver = SettingsResolver(key=key, settings=settings_instance)
            try:
                settings_instance = resolver.resolve(stack=stack)
            except KeyError:
                logger.info(
                    "Not including stack component settings with key `%s`.", key
                )

            if configuration_level not in settings_instance.LEVEL:
                raise TypeError(
                    f"The settings class {settings_instance.__class__} can not "
                    f"be specified on a {configuration_level.name} level."
                )
            validated_settings[key] = settings_instance

        return validated_settings

    def _get_step_spec(self, step: "BaseStep") -> StepSpec:
        """Gets the spec for a step.

        Args:
            step: The step for which to get the spec.

        Returns:
            The step spec.
        """
        return StepSpec(
            source=source_utils.resolve_class(step.__class__),
            upstream_steps=sorted(step.upstream_steps),
        )

    def _compile_step(
        self,
        step: "BaseStep",
        pipeline_settings: Dict[str, "BaseSettings"],
        pipeline_extra: Dict[str, Any],
        stack: "Stack",
    ) -> Step:
        """Compiles a ZenML step.

        Args:
            step: The step to compile.
            pipeline_settings: settings configured on the
                pipeline of the step.
            pipeline_extra: Extra values configured on the pipeline of the step.
            stack: The stack on which the pipeline will be run.

        Returns:
            The compiled step.
        """
        step_spec = self._get_step_spec(step=step)
        step_settings = self._filter_and_validate_settings(
            settings=step.configuration.settings,
            configuration_level=ConfigurationLevel.STEP,
            stack=stack,
        )

        merged_settings = {
            **pipeline_settings,
            **step_settings,
        }
        merged_extras = {**pipeline_extra, **step.configuration.extra}

        step.configure(
            settings=merged_settings,
            extra=merged_extras,
            merge=False,
        )

        complete_step_configuration = StepConfiguration(
            docstring=step.__doc__, **step.configuration.dict()
        )

        return Step(spec=step_spec, config=complete_step_configuration)

    def _compile_proto_pipeline(
        self, pipeline: "BasePipeline", stack: "Stack"
    ) -> Pb2Pipeline:
        """Compiles a ZenML pipeline into a TFX protobuf pipeline.

        Args:
            pipeline: The pipeline to compile.
            stack: The stack on which the pipeline will run.

        Raises:
            KeyError: If any step of the pipeline contains an invalid upstream
                step.

        Returns:
            The compiled proto pipeline.
        """
        # Connect the inputs/outputs of all steps in the pipeline
        tfx_components = {
            step.name: step.component for step in pipeline.steps.values()
        }

        # Add potential task dependencies that users specified
        for step in pipeline.steps.values():
            for upstream_step in step.upstream_steps:
                try:
                    upstream_node = tfx_components[upstream_step]
                except KeyError:
                    raise KeyError(
                        f"Unable to find upstream step `{upstream_step}` for step "
                        f"`{step.name}`. Available steps: {set(tfx_components)}."
                    )

                step.component.add_upstream_node(upstream_node)

        artifact_store = stack.artifact_store

        # We do not pass the metadata connection config here as it might not be
        # accessible. Instead it is queried from the active stack right before a
        # step is executed (see `BaseOrchestrator.run_step(...)`)
        intermediate_tfx_pipeline = tfx_pipeline.Pipeline(
            pipeline_name=pipeline.name,
            components=list(tfx_components.values()),
            pipeline_root=artifact_store.path,
            enable_cache=pipeline.enable_cache,
        )
        return TFXCompiler().compile(intermediate_tfx_pipeline)

    @staticmethod
    def _get_default_run_name(pipeline_name: str) -> str:
        """Gets the default name for a pipeline run.

        Args:
            pipeline_name: Name of the pipeline which will be run.

        Returns:
            Run name.
        """
        return (
            f"{pipeline_name}-"
            f'{datetime.now().strftime("%d_%h_%y-%H_%M_%S_%f")}'
        )

    @staticmethod
    def _get_sorted_steps(
        pb2_pipeline: Pb2Pipeline, steps: Dict[str, "BaseStep"]
    ) -> List[Tuple[str, "BaseStep"]]:
        """Sorts the steps of a pipeline.

        The resulting list of steps will be in an order that can be executed
        sequentially without any conflicts.

        Args:
            pb2_pipeline: Pipeline proto representation.
            steps: ZenML pipeline steps.

        Returns:
            The sorted steps.
        """
        mapping = {
            step.name: (name_in_pipeline, step)
            for name_in_pipeline, step in steps.items()
        }
        sorted_steps = []
        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node
            sorted_steps.append(mapping[pipeline_node.node_info.id])
        return sorted_steps

    @staticmethod
    def _ensure_required_stack_components_exist(
        stack: "Stack", steps: Sequence["Step"]
    ) -> None:
        """Ensures that the stack components required for each step exist.

        Args:
            stack: The stack on which the pipeline should be deployed.
            steps: The steps of the pipeline.

        Raises:
            StackValidationError: If a required stack component is missing.
        """
        available_step_operators = (
            {stack.step_operator.name} if stack.step_operator else set()
        )
        available_experiment_trackers = (
            {stack.experiment_tracker.name}
            if stack.experiment_tracker
            else set()
        )

        for step in steps:
            step_operator = step.config.step_operator
            if step_operator and step_operator not in available_step_operators:
                raise StackValidationError(
                    f"Step '{step.config.name}' requires step operator "
                    f"'{step_operator}' which is not configured in "
                    f"the stack '{stack.name}'. Available step operators: "
                    f"{available_step_operators}."
                )

            experiment_tracker = step.config.experiment_tracker
            if (
                experiment_tracker
                and experiment_tracker not in available_experiment_trackers
            ):
                raise StackValidationError(
                    f"Step '{step.config.name}' requires experiment tracker "
                    f"'{experiment_tracker}' which is not "
                    f"configured in the stack '{stack.name}'. Available "
                    f"experiment trackers: {available_experiment_trackers}."
                )
