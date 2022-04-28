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
import json
from abc import ABC, abstractmethod
from collections import OrderedDict
from json import JSONDecodeError
from typing import ClassVar, Dict, List, Optional, Tuple, Union

from ml_metadata import proto
from ml_metadata.metadata_store import metadata_store
from ml_metadata.proto import metadata_store_pb2
from tfx.dsl.compiler.constants import (
    PIPELINE_CONTEXT_TYPE_NAME,
    PIPELINE_RUN_CONTEXT_TYPE_NAME,
)

from zenml.artifacts.constants import (
    DATATYPE_PROPERTY_KEY,
    MATERIALIZER_PROPERTY_KEY,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.post_execution import (
    ArtifactView,
    PipelineRunView,
    PipelineView,
    StepView,
)
from zenml.stack import StackComponent
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_PIPELINE_PARAMETER_NAME,
)

logger = get_logger(__name__)


class BaseMetadataStore(StackComponent, ABC):
    """Base class for all ZenML metadata stores."""

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.METADATA_STORE

    upgrade_migration_enabled: bool = True
    _store: Optional[metadata_store.MetadataStore] = None

    @property
    def store(self) -> metadata_store.MetadataStore:
        """General property that hooks into TFX metadata store."""
        if self._store is None:
            config = self.get_tfx_metadata_config()
            self._store = metadata_store.MetadataStore(
                config,
                enable_upgrade_migration=self.upgrade_migration_enabled
                and isinstance(config, metadata_store_pb2.ConnectionConfig),
            )
        return self._store

    @abstractmethod
    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config."""
        raise NotImplementedError

    @property
    def step_type_mapping(self) -> Dict[int, str]:
        """Maps type_id's to step names."""
        return {
            type_.id: type_.name for type_ in self.store.get_execution_types()
        }

    def _check_if_executions_belong_to_pipeline(
        self,
        executions: List[proto.Execution],
        pipeline: PipelineView,
    ) -> bool:
        """Returns `True` if the executions are associated with the pipeline
        context."""
        for execution in executions:
            associated_contexts = self.store.get_contexts_by_execution(
                execution.id
            )
            for context in associated_contexts:
                if context.id == pipeline._id:  # noqa
                    return True
        return False

    def _get_step_view_from_execution(
        self, execution: proto.Execution
    ) -> StepView:
        """Get original StepView from an execution.

        Args:
            execution: proto.Execution object from mlmd store.

        Returns:
            Original `StepView` derived from the proto.Execution.
        """
        impl_name = self.step_type_mapping[execution.type_id].split(".")[-1]

        step_name_property = execution.custom_properties.get(
            INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_PIPELINE_PARAMETER_NAME,
            None,
        )
        if step_name_property:
            step_name = json.loads(step_name_property.string_value)
        else:
            raise KeyError(
                f"Step name missing for execution with ID {execution.id}. "
                f"This error probably occurs because you're using ZenML "
                f"version 0.5.4 or newer but your metadata store contains "
                f"data from previous versions."
            )

        step_parameters = {}
        for k, v in execution.custom_properties.items():
            if not k.startswith(INTERNAL_EXECUTION_PARAMETER_PREFIX):
                try:
                    step_parameters[k] = json.loads(v.string_value)
                except JSONDecodeError:
                    # this means there is a property in there that is neither
                    # an internal one or one created by zenml. Therefore, we can
                    # ignore it
                    pass

        # TODO [ENG-222]: This is a lot of querying to the metadata store. We
        #  should refactor and make it nicer. Probably it makes more sense
        #  to first get `executions_ids_for_current_run` and then filter on
        #  `event.execution_id in execution_ids_for_current_run`.
        # Core logic here is that we get the event of this particular execution
        # id that gives us the artifacts of this execution. We then go through
        # all `input` artifacts of this execution and get all events related to
        # that artifact. This in turn gives us other events for which this
        # artifact was an `output` artifact. Then we simply need to sort by
        # time to get the most recent execution (i.e. step) that produced that
        # particular artifact.
        events_for_execution = self.store.get_events_by_execution_ids(
            [execution.id]
        )

        parents_step_ids = set()
        for current_event in events_for_execution:
            if current_event.type == current_event.INPUT:
                # this means the artifact is an input artifact
                events_for_input_artifact = [
                    e
                    for e in self.store.get_events_by_artifact_ids(
                        [current_event.artifact_id]
                    )
                    # should be output type and should NOT be the same id as
                    # the execution we are querying and it should be BEFORE
                    # the time of the current event.
                    if e.type == e.OUTPUT
                    and e.execution_id != current_event.execution_id
                    and e.milliseconds_since_epoch
                    < current_event.milliseconds_since_epoch
                ]

                # sort by time
                events_for_input_artifact.sort(
                    key=lambda x: x.milliseconds_since_epoch  # type: ignore[no-any-return] # noqa
                )
                # take the latest one and add execution to the parents.
                parents_step_ids.add(events_for_input_artifact[-1].execution_id)

        return StepView(
            id_=execution.id,
            parents_step_ids=list(parents_step_ids),
            entrypoint_name=impl_name,
            name=step_name,
            parameters=step_parameters,
            metadata_store=self,
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
            logger.debug("Fetched pipeline with name '%s'", pipeline_name)
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
    ) -> Dict[str, PipelineRunView]:
        """Gets all runs for the given pipeline."""
        all_pipeline_runs = self.store.get_contexts_by_type(
            PIPELINE_RUN_CONTEXT_TYPE_NAME
        )
        runs: Dict[str, PipelineRunView] = OrderedDict()

        for run in all_pipeline_runs:
            executions = self.store.get_executions_by_context(run.id)
            if self._check_if_executions_belong_to_pipeline(
                executions, pipeline
            ):
                run_view = PipelineRunView(
                    id_=run.id,
                    name=run.name,
                    executions=executions,
                    metadata_store=self,
                )
                runs[run.name] = run_view

        logger.debug(
            "Fetched %d pipeline runs for pipeline named '%s'.",
            len(runs),
            pipeline.name,
        )

        return runs

    def get_pipeline_run(
        self, pipeline: PipelineView, run_name: str
    ) -> Optional[PipelineRunView]:
        """Gets a specific run for the given pipeline."""
        run = self.store.get_context_by_type_and_name(
            PIPELINE_RUN_CONTEXT_TYPE_NAME, run_name
        )

        if not run:
            # No context found for the given run name
            return None

        executions = self.store.get_executions_by_context(run.id)
        if self._check_if_executions_belong_to_pipeline(executions, pipeline):
            logger.debug("Fetched pipeline run with name '%s'", run_name)
            return PipelineRunView(
                id_=run.id,
                name=run.name,
                executions=executions,
                metadata_store=self,
            )

        logger.info("No pipeline run found for name '%s'", run_name)
        return None

    def get_pipeline_run_steps(
        self, pipeline_run: PipelineRunView
    ) -> Dict[str, StepView]:
        """Gets all steps for the given pipeline run."""
        steps: Dict[str, StepView] = OrderedDict()
        # reverse the executions as they get returned in reverse chronological
        # order from the metadata store
        for execution in reversed(pipeline_run._executions):  # noqa
            step = self._get_step_view_from_execution(execution)
            steps[step.name] = step

        logger.debug(
            "Fetched %d steps for pipeline run '%s'.",
            len(steps),
            pipeline_run.name,
        )

        return steps

    def get_step_by_id(self, step_id: int) -> StepView:
        """Gets a `StepView` by its ID"""
        execution = self.store.get_executions_by_id([step_id])[0]
        return self._get_step_view_from_execution(execution)

    def get_step_status(self, step: StepView) -> ExecutionStatus:
        """Gets the execution status of a single step."""
        proto = self.store.get_executions_by_id([step._id])[0]  # noqa
        state = proto.last_known_state

        if state == proto.COMPLETE:
            return ExecutionStatus.COMPLETED
        elif state == proto.RUNNING:
            return ExecutionStatus.RUNNING
        elif state == proto.CACHED:
            return ExecutionStatus.CACHED
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
            are both Dicts mapping artifact names
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

        inputs: Dict[str, ArtifactView] = {}
        outputs: Dict[str, ArtifactView] = {}

        # sort them according to artifact_id's so that the zip works.
        events.sort(key=lambda x: x.artifact_id)
        artifacts.sort(key=lambda x: x.id)

        for event_proto, artifact_proto in zip(events, artifacts):
            artifact_type = artifact_type_mapping[artifact_proto.type_id]
            artifact_name = event_proto.path.steps[0].key

            materializer = artifact_proto.properties[
                MATERIALIZER_PROPERTY_KEY
            ].string_value

            data_type = artifact_proto.properties[
                DATATYPE_PROPERTY_KEY
            ].string_value

            parent_step_id = step.id
            if event_proto.type == event_proto.INPUT:
                # In the case that this is an input event, we actually need
                # to resolve it via its parents outputs.
                for parent in step.parent_steps:
                    for a in parent.outputs.values():
                        if artifact_proto.id == a.id:
                            parent_step_id = parent.id

            artifact = ArtifactView(
                id_=event_proto.artifact_id,
                type_=artifact_type,
                uri=artifact_proto.uri,
                materializer=materializer,
                data_type=data_type,
                metadata_store=self,
                parent_step_id=parent_step_id,
            )

            if event_proto.type == event_proto.INPUT:
                inputs[artifact_name] = artifact
            elif event_proto.type == event_proto.OUTPUT:
                outputs[artifact_name] = artifact

        logger.debug(
            "Fetched %d inputs and %d outputs for step '%s'.",
            len(inputs),
            len(outputs),
            step.entrypoint_name,
        )

        return inputs, outputs

    def get_producer_step_from_artifact(
        self, artifact: ArtifactView
    ) -> StepView:
        """Returns original StepView from an ArtifactView.

        Args:
            artifact: ArtifactView to be queried.

        Returns:
            Original StepView that produced the artifact.
        """
        executions_ids = set(
            event.execution_id
            for event in self.store.get_events_by_artifact_ids([artifact.id])
            if event.type == event.OUTPUT
        )
        execution = self.store.get_executions_by_id(executions_ids)[0]
        return self._get_step_view_from_execution(execution)
