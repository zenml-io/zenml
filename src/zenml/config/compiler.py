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
import string
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.config.pipeline_configurations import (
    PipelineRunConfiguration,
    PipelineSpec,
)
from zenml.config.settings_resolver import SettingsResolver
from zenml.config.step_configurations import (
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.environment import get_run_environment_dict
from zenml.exceptions import PipelineInterfaceError, StackValidationError
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.utils import pydantic_utils, settings_utils, source_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.stack import Stack, StackComponent
    from zenml.steps import BaseStep

from zenml.logger import get_logger

logger = get_logger(__file__)


class Compiler:
    """Compiles ZenML pipelines to serializable representations."""

    def compile(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        run_configuration: PipelineRunConfiguration,
    ) -> Tuple[PipelineDeploymentBaseModel, PipelineSpec]:
        """Compiles a ZenML pipeline to a serializable representation.

        Args:
            pipeline: The pipeline to compile.
            stack: The stack on which the pipeline will run.
            run_configuration: The run configuration for this pipeline.

        Returns:
            The compiled pipeline deployment and spec
        """
        logger.debug("Compiling pipeline `%s`.", pipeline.name)
        # Copy the pipeline before we apply any run-level configurations so
        # we don't mess with the pipeline object/step objects in any way
        pipeline = copy.deepcopy(pipeline)
        self._apply_run_configuration(
            pipeline=pipeline, config=run_configuration
        )
        self._apply_stack_default_settings(pipeline=pipeline, stack=stack)
        self._verify_distinct_step_names(pipeline=pipeline)
        if run_configuration.run_name:
            self._verify_run_name(run_configuration.run_name)

        pipeline.connect(**pipeline.steps)

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
                pipeline_parameter_name=name,
                step=step,
                pipeline_settings=settings_to_passdown,
                pipeline_extra=pipeline.configuration.extra,
                stack=stack,
                pipeline_failure_hook_source=pipeline.configuration.failure_hook_source,
                pipeline_success_hook_source=pipeline.configuration.success_hook_source,
            )
            for name, step in self._get_sorted_steps(steps=pipeline.steps)
            if step._has_been_called
        }

        self._ensure_required_stack_components_exist(
            stack=stack, steps=list(steps.values())
        )

        run_name = run_configuration.run_name or self._get_default_run_name(
            pipeline_name=pipeline.name
        )

        deployment = PipelineDeploymentBaseModel(
            run_name_template=run_name,
            pipeline_configuration=pipeline.configuration,
            step_configurations=steps,
            client_environment=get_run_environment_dict(),
        )

        step_specs = [step.spec for step in steps.values()]
        pipeline_spec = PipelineSpec(steps=step_specs)
        logger.debug("Compiled pipeline deployment: %s", deployment)
        logger.debug("Compiled pipeline spec: %s", pipeline_spec)

        return deployment, pipeline_spec

    def compile_spec(self, pipeline: "BasePipeline") -> PipelineSpec:
        """Compiles a ZenML pipeline to a pipeline spec.

        This method can be used when a pipeline spec is needed but the full
        deployment including stack information is not required.

        Args:
            pipeline: The pipeline to compile.

        Returns:
            The compiled pipeline spec.
        """
        logger.debug(
            "Compiling pipeline spec for pipeline `%s`.", pipeline.name
        )
        # Copy the pipeline before we connect the steps so we don't mess with
        # the pipeline object/step objects in any way
        pipeline = copy.deepcopy(pipeline)
        self._verify_distinct_step_names(pipeline=pipeline)
        pipeline.connect(**pipeline.steps)

        steps = [
            self._get_step_spec(
                pipeline_parameter_name=pipeline_parameter_name,
                step=step,
            )
            for pipeline_parameter_name, step in self._get_sorted_steps(
                steps=pipeline.steps
            )
        ]
        pipeline_spec = PipelineSpec(steps=steps)
        logger.debug("Compiled pipeline spec: %s", pipeline_spec)
        return pipeline_spec

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
            enable_artifact_metadata=config.enable_artifact_metadata,
            settings=config.settings,
            extra=config.extra,
        )

        for step_name, step_config in config.steps.items():
            if step_name not in pipeline.steps:
                raise KeyError(f"No step with name {step_name}.")
            pipeline.steps[step_name]._apply_configuration(step_config)

        # Override `enable_cache` of all steps if set at run level
        if config.enable_cache is not None:
            for step_ in pipeline.steps.values():
                step_.configure(enable_cache=config.enable_cache)

        # Override `enable_artifact_metadata` of all steps if set at run level
        if config.enable_artifact_metadata is not None:
            for step_ in pipeline.steps.values():
                step_.configure(
                    enable_artifact_metadata=config.enable_artifact_metadata
                )

    def _apply_stack_default_settings(
        self, pipeline: "BasePipeline", stack: "Stack"
    ) -> None:
        """Applies stack default settings to a pipeline.

        Args:
            pipeline: The pipeline to which to apply the default settings.
            stack: The stack containing potential default settings.
        """
        pipeline_settings = pipeline.configuration.settings

        for component in stack.components.values():
            if not component.settings_class:
                continue

            settings_key = settings_utils.get_stack_component_setting_key(
                component
            )
            default_settings = self._get_default_settings(component)

            if settings_key in pipeline_settings:
                combined_settings = pydantic_utils.update_model(
                    default_settings, update=pipeline_settings[settings_key]
                )
                pipeline_settings[settings_key] = combined_settings
            else:
                pipeline_settings[settings_key] = default_settings

        pipeline.configure(settings=pipeline_settings, merge=False)

    def _get_default_settings(
        self,
        stack_component: "StackComponent",
    ) -> "BaseSettings":
        """Gets default settings configured on a stack component.

        Args:
            stack_component: The stack component for which to get the settings.

        Returns:
            The settings configured on the stack component.
        """
        assert stack_component.settings_class
        # Exclude additional config attributes that aren't part of the settings
        field_names = set(stack_component.settings_class.__fields__)
        default_settings = stack_component.settings_class.parse_obj(
            stack_component.config.dict(
                include=field_names, exclude_unset=True, exclude_defaults=True
            )
        )
        return default_settings

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

    @staticmethod
    def _verify_run_name(run_name: str) -> None:
        """Verifies that the run name contains only valid placeholders.

        Args:
            run_name: The run name to verify.

        Raises:
            ValueError: If the run name contains invalid placeholders.
        """
        valid_placeholder_names = {"date", "time"}
        placeholders = {
            v[1] for v in string.Formatter().parse(run_name) if v[1]
        }
        if not placeholders.issubset(valid_placeholder_names):
            raise ValueError(
                f"Invalid run name {run_name}. Only the placeholders "
                f"{valid_placeholder_names} are allowed in run names."
            )

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
                    "Not including stack component settings with key `%s`.",
                    key,
                )
                continue

            if configuration_level not in settings_instance.LEVEL:
                raise TypeError(
                    f"The settings class {settings_instance.__class__} can not "
                    f"be specified on a {configuration_level.name} level."
                )
            validated_settings[key] = settings_instance

        return validated_settings

    def _get_step_spec(
        self,
        pipeline_parameter_name: str,
        step: "BaseStep",
    ) -> StepSpec:
        """Gets the spec for a step.

        Args:
            pipeline_parameter_name: Name of the step in the pipeline.
            step: The step for which to get the spec.

        Returns:
            The step spec.
        """
        return StepSpec(
            source=source_utils.resolve_class(step.__class__),
            upstream_steps=sorted(step.upstream_steps),
            inputs=step.inputs,
            pipeline_parameter_name=pipeline_parameter_name,
        )

    def _compile_step(
        self,
        pipeline_parameter_name: str,
        step: "BaseStep",
        pipeline_settings: Dict[str, "BaseSettings"],
        pipeline_extra: Dict[str, Any],
        stack: "Stack",
        pipeline_failure_hook_source: Optional[str] = None,
        pipeline_success_hook_source: Optional[str] = None,
    ) -> Step:
        """Compiles a ZenML step.

        Args:
            pipeline_parameter_name: Name of the step in the pipeline.
            step: The step to compile.
            pipeline_settings: settings configured on the
                pipeline of the step.
            pipeline_extra: Extra values configured on the pipeline of the step.
            stack: The stack on which the pipeline will be run.
            pipeline_failure_hook_source: Source for the failure hook.
            pipeline_success_hook_source: Source for the success hook.

        Returns:
            The compiled step.
        """
        step_spec = self._get_step_spec(
            pipeline_parameter_name=pipeline_parameter_name, step=step
        )
        step_settings = self._filter_and_validate_settings(
            settings=step.configuration.settings,
            configuration_level=ConfigurationLevel.STEP,
            stack=stack,
        )
        step_extra = step.configuration.extra
        step_on_failure_hook_source = step.configuration.failure_hook_source
        step_on_success_hook_source = step.configuration.success_hook_source

        step.configure(
            settings=pipeline_settings,
            extra=pipeline_extra,
            on_failure=pipeline_failure_hook_source,
            on_success=pipeline_success_hook_source,
            merge=False,
        )
        step.configure(
            settings=step_settings,
            extra=step_extra,
            on_failure=step_on_failure_hook_source,
            on_success=step_on_success_hook_source,
            merge=True,
        )

        complete_step_configuration = StepConfiguration(
            **step.configuration.dict()
        )

        return Step(spec=step_spec, config=complete_step_configuration)

    @staticmethod
    def _get_default_run_name(pipeline_name: str) -> str:
        """Gets the default name for a pipeline run.

        Args:
            pipeline_name: Name of the pipeline which will be run.

        Returns:
            Run name.
        """
        return f"{pipeline_name}-{{date}}-{{time}}"

    @staticmethod
    def _get_sorted_steps(
        steps: Dict[str, "BaseStep"]
    ) -> List[Tuple[str, "BaseStep"]]:
        """Sorts the steps of a pipeline using topological sort.

        The resulting list of steps will be in an order that can be executed
        sequentially without any conflicts.

        Args:
            steps: ZenML pipeline steps.

        Returns:
            The sorted steps.
        """
        from zenml.orchestrators.dag_runner import reverse_dag
        from zenml.orchestrators.topsort import topsorted_layers

        # Sort step names using topological sort
        dag: Dict[str, List[str]] = {
            step.name: list(step.upstream_steps) for step in steps.values()
        }
        reversed_dag: Dict[str, List[str]] = reverse_dag(dag)
        layers = topsorted_layers(
            nodes=[step.name for step in steps.values()],
            get_node_id_fn=lambda node: node,
            get_parent_nodes=lambda node: dag[node],
            get_child_nodes=lambda node: reversed_dag[node],
        )
        sorted_step_names = [step for layer in layers for step in layer]

        # Construct pipeline name to step mapping
        step_name_to_name_in_pipeline: Dict[str, str] = {
            step.name: name_in_pipeline
            for name_in_pipeline, step in steps.items()
        }
        sorted_names_in_pipeline: List[str] = [
            step_name_to_name_in_pipeline[step_name]
            for step_name in sorted_step_names
        ]
        sorted_steps: List[Tuple[str, "BaseStep"]] = [
            (name_in_pipeline, steps[name_in_pipeline])
            for name_in_pipeline in sorted_names_in_pipeline
        ]
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
