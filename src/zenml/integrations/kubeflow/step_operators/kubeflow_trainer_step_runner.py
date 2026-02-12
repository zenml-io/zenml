#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Kubeflow Trainer-specific step runner with distributed side-effect gating."""

import inspect
from typing import TYPE_CHECKING, Dict, List

from zenml.integrations.kubeflow.step_operators.distributed_utils import (
    is_primary_distributed_replica,
)
from zenml.logger import get_logger
from zenml.orchestrators.step_runner import StepRunner
from zenml.steps.step_context import StepContext
from zenml.steps.utils import parse_return_type_annotations
from zenml.utils import env_utils

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse

logger = get_logger(__name__)


class KubeflowTrainerStepRunner(StepRunner):
    """Step runner that only publishes ZenML lifecycle events on rank-0."""

    def run(
        self,
        pipeline_run: "PipelineRunResponse",
        step_run: "StepRunResponse",
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
        output_artifact_uris: Dict[str, str],
        step_run_info: "StepRunInfo",
    ) -> None:
        """Runs the step with distributed publish gating.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            input_artifacts: The input artifact versions of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            step_run_info: The step run info.
        """
        if is_primary_distributed_replica():
            super().run(
                pipeline_run=pipeline_run,
                step_run=step_run,
                input_artifacts=input_artifacts,
                output_artifact_uris=output_artifact_uris,
                step_run_info=step_run_info,
            )
            return

        logger.info(
            "Detected non-primary distributed replica for step `%s`; "
            "executing user code without publishing ZenML artifacts or status.",
            step_run.name,
        )

        self._run_worker_replica(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )

    def _run_worker_replica(
        self,
        pipeline_run: "PipelineRunResponse",
        step_run: "StepRunResponse",
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
        output_artifact_uris: Dict[str, str],
        step_run_info: "StepRunInfo",
    ) -> None:
        """Executes the step entrypoint for a non-primary distributed replica.

        This path intentionally avoids ZenML run-state and artifact publishing.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            input_artifacts: Input artifacts for the step.
            output_artifact_uris: Output artifact URIs for this execution.
            step_run_info: Runtime information for the step run.
        """
        step_instance = self._load_step()
        output_materializers = self._load_output_materializers()

        spec = inspect.getfullargspec(inspect.unwrap(step_instance.entrypoint))
        output_annotations = parse_return_type_annotations(
            func=step_instance.entrypoint
        )

        self._evaluate_artifact_names_in_collections(
            step_run,
            output_annotations,
            [
                output_artifact_uris,
                output_materializers,
            ],
        )

        self._stack.prepare_step_run(info=step_run_info)

        step_context = StepContext(
            pipeline_run=pipeline_run,
            step_run=step_run,
            output_materializers=output_materializers,
            output_artifact_uris=output_artifact_uris,
            output_artifact_configs={
                key: value.artifact_config
                for key, value in output_annotations.items()
            },
        )

        step_failed = False
        try:
            with step_context:
                function_params = self._parse_inputs(
                    args=spec.args,
                    annotations=spec.annotations,
                    input_artifacts=input_artifacts,
                )

                step_environment = env_utils.get_runtime_environment(
                    config=step_run.config,
                    stack=self._stack,
                )
                secret_environment = env_utils.get_runtime_secret_environment(
                    config=step_run.config,
                    stack=self._stack,
                )
                step_environment.update(secret_environment)

                with env_utils.temporary_environment(step_environment):
                    return_values = step_instance.call_entrypoint(
                        **function_params
                    )

                self._validate_outputs(return_values, output_annotations)
        except BaseException:  # noqa: E722
            step_failed = True
            raise
        finally:
            self._stack.cleanup_step_run(
                info=step_run_info,
                step_failed=step_failed,
            )
