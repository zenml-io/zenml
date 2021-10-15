#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from abc import abstractmethod
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from ml_metadata.metadata_store import metadata_store
from tfx.dsl.compiler.constants import (
    PIPELINE_CONTEXT_TYPE_NAME,
    PIPELINE_RUN_CONTEXT_TYPE_NAME,
)

from zenml.artifacts.base_artifact import MATERIALIZERS_PROPERTY_KEY
from zenml.core.base_component import BaseComponent
from zenml.core.component_factory import metadata_store_factory
from zenml.enums import ExecutionStatus, MLMetadataTypes
from zenml.logger import get_logger
from zenml.post_execution import (
    ArtifactView,
    PipelineRunView,
    PipelineView,
    StepView,
)
from zenml.utils.path_utils import get_zenml_config_dir

logger = get_logger(__name__)


@metadata_store_factory.register(MLMetadataTypes.base)
class BaseMetadataStore(BaseComponent):
    """Metadata store base class to track metadata of zenml first class
    citizens."""

    _run_type_name: str = "pipeline_run"
    _node_type_name: str = "node"
    _METADATA_STORE_DIR_NAME = "metadata_stores"

    @property
    def store(self):
        """General property that hooks into TFX metadata store."""
        return metadata_store.MetadataStore(self.get_tfx_metadata_config())

    @abstractmethod
    def get_tfx_metadata_config(self):
        """Return tfx metadata config."""

    def get_serialization_dir(self) -> str:
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._METADATA_STORE_DIR_NAME
        )

    def get_pipelines(self) -> List[PipelineView]:
        """Returns a list of all pipelines stored in this metadata store."""
        pipelines = []
        for pipeline_context in self.store.get_contexts_by_type(
            PIPELINE_CONTEXT_TYPE_NAME
        ):
            pipeline = PipelineView(
                id_=pipeline_context.id,
                name=pipeline_context.name,
                metadata_store=self,
            )
            pipelines.append(pipeline)

        logger.debug("Fetched %d pipelines.", len(pipelines))
        return pipelines

    def get_pipeline(self, pipeline_name: str) -> Optional[PipelineView]:
        """Returns a pipeline for the given name."""
        pipeline_context = self.store.get_context_by_type_and_name(
            PIPELINE_CONTEXT_TYPE_NAME, pipeline_name
        )
        if pipeline_context:
            logger.debug("Fetched pipelines with name '%s'", pipeline_name)
            return PipelineView(
                id_=pipeline_context.id,
                name=pipeline_context.name,
                metadata_store=self,
            )
        else:
            logger.info("No pipelines found for name '%s'", pipeline_name)
            return None

    def get_pipeline_runs(
        self, pipeline: PipelineView
    ) -> List[PipelineRunView]:
        """Gets all runs for the given pipeline."""
        all_pipeline_runs = self.store.get_contexts_by_type(
            PIPELINE_RUN_CONTEXT_TYPE_NAME
        )
        runs = []

        for run in all_pipeline_runs:
            run_executions = self.store.get_executions_by_context(run.id)
            if run_executions:
                associated_contexts = self.store.get_contexts_by_execution(
                    run_executions[0].id
                )
                for context in associated_contexts:
                    if context.id == pipeline._id:  # noqa
                        # Run is of this pipeline
                        runs.append(
                            PipelineRunView(
                                id_=run.id,
                                name=run.name,
                                executions=run_executions,
                                metadata_store=self,
                            )
                        )
                        break

        logger.debug(
            "Fetched %d pipeline runs for pipeline named '%s'.",
            len(runs),
            pipeline.name,
        )

        return runs

    def get_pipeline_run_steps(
        self, pipeline_run: PipelineRunView
    ) -> Dict[str, StepView]:
        """Gets all steps for the given pipeline run."""
        # maps type_id's to step names
        step_type_mapping: Dict[int, str] = {
            type_.id: type_.name for type_ in self.store.get_execution_types()
        }

        steps: Dict[str, StepView] = OrderedDict()
        # reverse the executions as they get returned in reverse chronological
        # order from the metadata store
        for execution in reversed(pipeline_run._executions):  # noqa
            step_name = step_type_mapping[execution.type_id]
            # TODO [HIGH]: why is the name like this?
            step_prefix = "zenml.steps.base_step."
            if step_name.startswith(step_prefix):
                step_name = step_name[len(step_prefix) :]  # TODO [LOW]: black

            step_parameters = {
                k: v.string_value  # TODO [LOW]: Can we get the actual type?
                for k, v in execution.custom_properties.items()
            }

            step = StepView(
                id_=execution.id,
                name=step_name,
                parameters=step_parameters,
                metadata_store=self,
            )
            steps[step_name] = step

        logger.debug(
            "Fetched %d steps for pipeline run '%s'.",
            len(steps),
            pipeline_run.name,
        )

        return steps

    def get_step_status(self, step: StepView) -> ExecutionStatus:
        proto = self.store.get_executions_by_id([step._id])[0]  # noqa
        state = proto.last_known_state

        if state == proto.COMPLETE or state == proto.CACHED:
            return ExecutionStatus.COMPLETED
        elif state == proto.RUNNING:
            return ExecutionStatus.RUNNING
        else:
            return ExecutionStatus.FAILED

    def get_step_artifacts(
        self, step: StepView
    ) -> Tuple[Dict[str, ArtifactView], Dict[str, ArtifactView]]:
        """Returns input and output artifacts for the given step.

        Args:
            step: The step for which to get the artifacts.

        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both OrderedDicts mapping artifact names
            to the input and output artifacts respectively.
        """
        # maps artifact types to their string representation
        artifact_type_mapping = {
            type_.id: type_.name for type_ in self.store.get_artifact_types()
        }

        events = self.store.get_events_by_execution_ids([step._id])  # noqa
        artifacts = self.store.get_artifacts_by_id(
            [event.artifact_id for event in events]
        )

        inputs: Dict[str, ArtifactView] = OrderedDict()
        outputs: Dict[str, ArtifactView] = OrderedDict()

        for event_proto, artifact_proto in zip(events, artifacts):
            artifact_type = artifact_type_mapping[artifact_proto.type_id]
            artifact_name = event_proto.path.steps[0].key

            materializer = artifact_proto.properties[
                MATERIALIZERS_PROPERTY_KEY
            ].string_value

            artifact = ArtifactView(
                id_=event_proto.artifact_id,
                type_=artifact_type,
                uri=artifact_proto.uri,
                materializer=materializer,
            )

            if event_proto.type == event_proto.INPUT:
                inputs[artifact_name] = artifact
            elif event_proto.type == event_proto.OUTPUT:
                outputs[artifact_name] = artifact

        logger.debug(
            "Fetched %d inputs and %d outputs for step '%s'.",
            len(inputs),
            len(outputs),
            step.name,
        )

        return inputs, outputs

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_metadata_store_"
