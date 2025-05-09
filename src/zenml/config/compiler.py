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
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
)

from zenml import __version__
from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.settings_resolver import SettingsResolver
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfigurationUpdate,
    StepSpec,
)
from zenml.environment import get_run_environment_dict
from zenml.exceptions import StackValidationError
from zenml.models import PipelineDeploymentBase
from zenml.pipelines.run_utils import get_default_run_name
from zenml.utils import pydantic_utils, settings_utils

if TYPE_CHECKING:
    from zenml.pipelines.pipeline_definition import Pipeline
    from zenml.stack import Stack, StackComponent
    from zenml.steps.step_invocation import StepInvocation

from zenml.logger import get_logger

logger = get_logger(__file__)


def get_zenml_versions() -> Tuple[str, str]:
    """Returns the version of ZenML on the client and server side.

    Returns:
        the ZenML versions on the client and server side respectively.
    """
    from zenml.client import Client

    client = Client()
    server_version = client.zen_store.get_store_info().version

    return __version__, server_version


class Compiler:
    """Compiles ZenML pipelines to serializable representations."""

    def compile(
        self,
        pipeline: "Pipeline",
        stack: "Stack",
        run_configuration: PipelineRunConfiguration,
    ) -> PipelineDeploymentBase:
        """Compiles a ZenML pipeline to a serializable representation.

        Args:
            pipeline: The pipeline to compile.
            stack: The stack on which the pipeline will run.
            run_configuration: The run configuration for this pipeline.

        Returns:
            The compiled pipeline deployment.
        """
        logger.debug("Compiling pipeline `%s`.", pipeline.name)
        # Copy the pipeline before we apply any run-level configurations, so
        # we don't mess with the pipeline object/step objects in any way
        pipeline = copy.deepcopy(pipeline)
        self._apply_run_configuration(
            pipeline=pipeline, config=run_configuration
        )
        convert_component_shortcut_settings_keys(
            pipeline.configuration.settings, stack=stack
        )

        self._apply_stack_default_settings(pipeline=pipeline, stack=stack)
        if run_configuration.run_name:
            self._verify_run_name(
                run_configuration.run_name,
                pipeline.configuration.substitutions,
            )

        pipeline_settings = self._filter_and_validate_settings(
            settings=pipeline.configuration.settings,
            configuration_level=ConfigurationLevel.PIPELINE,
            stack=stack,
        )
        with pipeline.__suppress_configure_warnings__():
            pipeline.configure(settings=pipeline_settings, merge=False)

        steps = {
            invocation_id: self._compile_step_invocation(
                invocation=invocation,
                stack=stack,
                step_config=run_configuration.steps.get(invocation_id),
                pipeline_configuration=pipeline.configuration,
            )
            for invocation_id, invocation in self._get_sorted_invocations(
                pipeline=pipeline
            )
        }

        self._ensure_required_stack_components_exist(stack=stack, steps=steps)

        run_name = run_configuration.run_name or get_default_run_name(
            pipeline_name=pipeline.name
        )

        client_version, server_version = get_zenml_versions()

        step_specs = [step.spec for step in steps.values()]
        pipeline_spec = self._compute_pipeline_spec(
            pipeline=pipeline, step_specs=step_specs
        )

        deployment = PipelineDeploymentBase(
            run_name_template=run_name,
            pipeline_configuration=pipeline.configuration,
            step_configurations=steps,
            client_environment=get_run_environment_dict(),
            client_version=client_version,
            server_version=server_version,
            pipeline_version_hash=pipeline._compute_unique_identifier(
                pipeline_spec=pipeline_spec
            ),
            pipeline_spec=pipeline_spec,
        )

        logger.debug("Compiled pipeline deployment: %s", deployment)

        return deployment

    def compile_spec(self, pipeline: "Pipeline") -> PipelineSpec:
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
        # Copy the pipeline before we connect the steps, so we don't mess with
        # the pipeline object/step objects in any way
        pipeline = copy.deepcopy(pipeline)

        invocations = [
            self._get_step_spec(invocation=invocation)
            for _, invocation in self._get_sorted_invocations(
                pipeline=pipeline
            )
        ]

        pipeline_spec = self._compute_pipeline_spec(
            pipeline=pipeline, step_specs=invocations
        )
        logger.debug("Compiled pipeline spec: %s", pipeline_spec)
        return pipeline_spec

    def _apply_run_configuration(
        self, pipeline: "Pipeline", config: PipelineRunConfiguration
    ) -> None:
        """Applies run configurations to the pipeline and its steps.

        Args:
            pipeline: The pipeline to configure.
            config: The run configurations.
        """
        with pipeline.__suppress_configure_warnings__():
            pipeline.configure(
                enable_cache=config.enable_cache,
                enable_artifact_metadata=config.enable_artifact_metadata,
                enable_artifact_visualization=config.enable_artifact_visualization,
                enable_step_logs=config.enable_step_logs,
                enable_pipeline_logs=config.enable_pipeline_logs,
                settings=config.settings,
                tags=config.tags,
                extra=config.extra,
                model=config.model,
                parameters=config.parameters,
            )

        invalid_step_configs = set(config.steps) - set(pipeline.invocations)
        if invalid_step_configs:
            logger.warning(
                f"Configuration for step invocations {invalid_step_configs} "
                "cannot be applied to any pipeline step invocations, "
                "ignoring..."
            )

        for key in invalid_step_configs:
            config.steps.pop(key)

        # Override `enable_cache` of all steps if set at run level
        if config.enable_cache is not None:
            for invocation in pipeline.invocations.values():
                invocation.step.configure(enable_cache=config.enable_cache)

        # Override `enable_artifact_metadata` of all steps if set at run level
        if config.enable_artifact_metadata is not None:
            for invocation in pipeline.invocations.values():
                invocation.step.configure(
                    enable_artifact_metadata=config.enable_artifact_metadata
                )

        # Override `enable_artifact_visualization` if set at run level
        if config.enable_artifact_visualization is not None:
            for invocation in pipeline.invocations.values():
                invocation.step.configure(
                    enable_artifact_visualization=config.enable_artifact_visualization
                )

        # Override `enable_step_logs` if set at run level
        if config.enable_step_logs is not None:
            for invocation in pipeline.invocations.values():
                invocation.step.configure(
                    enable_step_logs=config.enable_step_logs
                )

    def _apply_stack_default_settings(
        self, pipeline: "Pipeline", stack: "Stack"
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

        with pipeline.__suppress_configure_warnings__():
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
        field_names = set(stack_component.settings_class.model_fields.keys())
        default_settings = stack_component.settings_class.model_validate(
            stack_component.config.model_dump(
                include=field_names, exclude_unset=True, exclude_defaults=True
            )
        )
        return default_settings

    @staticmethod
    def _verify_run_name(
        run_name: str,
        substitutions: Dict[str, str],
    ) -> None:
        """Verifies that the run name contains only valid placeholders.

        Args:
            run_name: The run name to verify.
            substitutions: The substitutions to be used in the run name.

        Raises:
            ValueError: If the run name contains invalid placeholders.
        """
        valid_placeholder_names = {"date", "time"}.union(
            set(substitutions.keys())
        )
        placeholders = {
            v[1] for v in string.Formatter().parse(run_name) if v[1]
        }
        if not placeholders.issubset(valid_placeholder_names):
            raise ValueError(
                f"Invalid run name {run_name}. Only the placeholders "
                f"{valid_placeholder_names} are allowed in run names."
            )

    def _verify_upstream_steps(
        self, invocation: "StepInvocation", pipeline: "Pipeline"
    ) -> None:
        """Verifies the upstream steps for a step invocation.

        Args:
            invocation: The step invocation for which to verify the upstream
                steps.
            pipeline: The parent pipeline of the invocation.

        Raises:
            RuntimeError: If an upstream step is missing.
        """
        available_steps = set(pipeline.invocations)
        invalid_upstream_steps = invocation.upstream_steps - available_steps

        if invalid_upstream_steps:
            raise RuntimeError(
                f"Invalid upstream steps: {invalid_upstream_steps}. Available "
                f"steps in this pipeline: {available_steps}."
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

            if settings_instance.model_extra:
                logger.warning(
                    "Ignoring invalid setting attributes `%s` defined for key `%s`.",
                    list(settings_instance.model_extra),
                    key,
                )
                settings_instance = settings_instance.model_validate(
                    settings_instance.model_dump(
                        exclude=set(settings_instance.model_extra),
                        exclude_unset=True,
                    )
                )

            if not settings_instance.model_fields_set:
                # There are no values defined on the settings instance, don't
                # include them in the deployment
                continue

            validated_settings[key] = settings_instance

        return validated_settings

    def _get_step_spec(
        self,
        invocation: "StepInvocation",
    ) -> StepSpec:
        """Gets the spec for a step invocation.

        Args:
            invocation: The invocation for which to get the spec.

        Returns:
            The step spec.
        """
        inputs = {
            key: InputSpec(
                step_name=artifact.invocation_id,
                output_name=artifact.output_name,
            )
            for key, artifact in invocation.input_artifacts.items()
        }
        return StepSpec(
            source=invocation.step.resolve(),
            upstream_steps=sorted(invocation.upstream_steps),
            inputs=inputs,
            pipeline_parameter_name=invocation.id,
        )

    def _compile_step_invocation(
        self,
        invocation: "StepInvocation",
        stack: "Stack",
        step_config: Optional["StepConfigurationUpdate"],
        pipeline_configuration: "PipelineConfiguration",
    ) -> Step:
        """Compiles a ZenML step.

        Args:
            invocation: The step invocation to compile.
            stack: The stack on which the pipeline will be run.
            step_config: Run configuration for the step.
            pipeline_configuration: Configuration for the pipeline.

        Returns:
            The compiled step.
        """
        # Copy the invocation (including its referenced step) before we apply
        # the step configuration which is exclusive to this invocation.
        invocation = copy.deepcopy(invocation)

        step = invocation.step
        if step_config:
            step._apply_configuration(
                step_config, runtime_parameters=invocation.parameters
            )

        convert_component_shortcut_settings_keys(
            step.configuration.settings, stack=stack
        )
        step_spec = self._get_step_spec(invocation=invocation)
        step_settings = self._filter_and_validate_settings(
            settings=step.configuration.settings,
            configuration_level=ConfigurationLevel.STEP,
            stack=stack,
        )
        step.configure(
            settings=step_settings,
            merge=False,
        )

        parameters_to_ignore = (
            set(step_config.parameters) if step_config else set()
        )
        step_configuration_overrides = invocation.finalize(
            parameters_to_ignore=parameters_to_ignore
        )
        full_step_config = (
            step_configuration_overrides.apply_pipeline_configuration(
                pipeline_configuration=pipeline_configuration
            )
        )
        return Step(
            spec=step_spec,
            config=full_step_config,
            step_config_overrides=step_configuration_overrides,
        )

    def _get_sorted_invocations(
        self,
        pipeline: "Pipeline",
    ) -> List[Tuple[str, "StepInvocation"]]:
        """Sorts the step invocations of a pipeline using topological sort.

        The resulting list of invocations will be in an order that can be
        executed sequentially without any conflicts.

        Args:
            pipeline: The pipeline of which to sort the invocations

        Returns:
            The sorted steps.
        """
        from zenml.orchestrators.dag_runner import reverse_dag
        from zenml.orchestrators.topsort import topsorted_layers

        # Sort step names using topological sort
        dag: Dict[str, List[str]] = {}
        for name, step in pipeline.invocations.items():
            self._verify_upstream_steps(invocation=step, pipeline=pipeline)
            dag[name] = list(step.upstream_steps)

        reversed_dag: Dict[str, List[str]] = reverse_dag(dag)
        layers = topsorted_layers(
            nodes=list(dag),
            get_node_id_fn=lambda node: node,
            get_parent_nodes=lambda node: dag[node],
            get_child_nodes=lambda node: reversed_dag[node],
        )
        sorted_step_names = [step for layer in layers for step in layer]
        sorted_invocations: List[Tuple[str, "StepInvocation"]] = [
            (name_in_pipeline, pipeline.invocations[name_in_pipeline])
            for name_in_pipeline in sorted_step_names
        ]
        return sorted_invocations

    @staticmethod
    def _ensure_required_stack_components_exist(
        stack: "Stack", steps: Mapping[str, "Step"]
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

        for name, step in steps.items():
            step_operator = step.config.step_operator
            if step_operator and step_operator not in available_step_operators:
                raise StackValidationError(
                    f"Step `{name}` requires step operator "
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
                    f"Step `{name}` requires experiment tracker "
                    f"'{experiment_tracker}' which is not "
                    f"configured in the stack '{stack.name}'. Available "
                    f"experiment trackers: {available_experiment_trackers}."
                )

    @staticmethod
    def _compute_pipeline_spec(
        pipeline: "Pipeline", step_specs: List["StepSpec"]
    ) -> "PipelineSpec":
        """Computes the pipeline spec.

        Args:
            pipeline: The pipeline for which to compute the spec.
            step_specs: The step specs for the pipeline.

        Returns:
            The pipeline spec.

        Raises:
            ValueError: If the pipeline has no steps.
        """
        if not step_specs:
            raise ValueError(
                f"Pipeline '{pipeline.name}' cannot be compiled because it has "
                f"no steps. Please make sure that your steps are decorated "
                "with `@step` and that at least one step is called within the "
                "pipeline. For more information, see "
                "https://docs.zenml.io/user-guides/starter-guide."
            )

        additional_spec_args: Dict[str, Any] = {
            "source": pipeline.resolve(),
            "parameters": pipeline._parameters,
        }

        return PipelineSpec(steps=step_specs, **additional_spec_args)


def convert_component_shortcut_settings_keys(
    settings: Dict[str, "BaseSettings"], stack: "Stack"
) -> None:
    """Convert component shortcut settings keys.

    Args:
        settings: Dictionary of settings.
        stack: The stack that the pipeline will run on.

    Raises:
        ValueError: If stack component settings were defined both using the
            full and the shortcut key.
    """
    for component in stack.components.values():
        shortcut_key = str(component.type)
        if component_settings := settings.pop(shortcut_key, None):
            key = settings_utils.get_stack_component_setting_key(component)
            if key in settings:
                raise ValueError(
                    f"Duplicate settings provided for your {shortcut_key} "
                    f"using the keys {shortcut_key} and {key}. Remove settings "
                    "for one of them to fix this error."
                )

            settings[key] = component_settings
