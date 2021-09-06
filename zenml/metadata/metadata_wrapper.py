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


from abc import abstractmethod
from typing import Text

from ml_metadata.metadata_store import metadata_store
from pydantic import BaseModel

from zenml.enums import MLMetadataTypes, PipelineStatusTypes
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger

logger = get_logger(__name__)


class BaseMetadataStore(BaseModel):
    """Metadata store base class to track metadata of zenml first class
    citizens."""

    store_type: MLMetadataTypes = None
    run_type_name: str = "pipeline_run"
    node_type_name: str = "node"

    @property
    def store(self):
        """General property that hooks into TFX metadata store."""
        return metadata_store.MetadataStore(self.get_tfx_metadata_config())

    @abstractmethod
    def get_tfx_metadata_config(self):
        """Return tfx metadata config."""

    def get_data_pipeline_names_from_datasource_name(
        self, datasource_name: Text
    ):
        """Gets all data pipeline names from the datasource name.

        Args:
          datasource_name: name of datasource.
          datasource_name: Text:

        Returns:

        """
        from zenml.pipelines.data_pipeline import DataPipeline

        run_contexts = self.store.get_contexts_by_type(self.run_type_name)

        # TODO [LOW]:
        #  get the data pipelines only by doing an ugly hack. These data
        #  pipelines will always start with `data_`. This needs to change soon
        run_contexts = [
            x
            for x in run_contexts
            if x.name.startswith(DataPipeline.PIPELINE_TYPE)
        ]

        # now filter to the datasource name through executions
        pipelines_names = []
        for c in run_contexts:
            es = self.store.get_executions_by_context(c.id)
            for e in es:
                if (
                    "name" in e.custom_properties
                    and e.custom_properties["name"].string_value
                    == datasource_name
                ):
                    pipelines_names.append(c.name)
        return pipelines_names

    def get_pipeline_status(self, pipeline) -> Text:
        """Query metadata store to find status of pipeline.

        Args:
          pipeline(BasePipeline): a ZenML pipeline object

        Returns:

        """
        try:
            components_status = self.get_components_status(pipeline)
        except Exception:
            return PipelineStatusTypes.NotStarted.name

        for status in components_status.values():
            if status != "complete" and status != "cached":
                return PipelineStatusTypes.Running.name
        return PipelineStatusTypes.Succeeded.name

    def get_pipeline_executions(self, pipeline):
        """Get executions of pipeline.

        Args:
          pipeline(BasePipeline): a ZenML pipeline object

        Returns:

        """
        c = self.get_pipeline_context(pipeline)
        return self.store.get_executions_by_context(c.id)

    def get_components_status(self, pipeline):
        """Returns status of components in pipeline.

        Args:
          pipeline(BasePipeline): a ZenML pipeline object
        Returns: dict of type { component_name : component_status }

        Returns:

        """
        state_mapping = {
            0: "unknown",
            1: "new",
            2: "running",
            3: "complete",
            4: "failed",
            5: "cached",
            6: "cancelled",
        }
        result = {}
        pipeline_executions = self.get_pipeline_executions(pipeline)
        for e in pipeline_executions:
            contexts = self.store.get_contexts_by_execution(e.id)
            node_contexts = [c for c in contexts if c.type_id == 3]
            if node_contexts:
                component_name = node_contexts[0].name.split(".")[-1]
                result[component_name] = state_mapping[e.last_known_state]

        return result

    def get_artifacts_by_component(self, pipeline, component_name: Text):
        """Gets artifacts by component name.

        Args:
          pipeline(BasePipeline): a ZenML pipeline object
          component_name:
          component_name: Text:

        Returns:

        """
        # First get the context of the component and its artifacts
        component_context = [
            c
            for c in self.store.get_contexts_by_type(self.node_type_name)
            if c.name.endswith(component_name)
        ][0]
        component_artifacts = self.store.get_artifacts_by_context(
            component_context.id
        )

        # Second, get the context of the particular pipeline and its artifacts
        pipeline_context = self.store.get_context_by_type_and_name(
            self.run_type_name, pipeline.pipeline_name
        )
        pipeline_artifacts = self.store.get_artifacts_by_context(
            pipeline_context.id
        )

        # Figure out the matching ids
        return [
            a
            for a in component_artifacts
            if a.id in [p.id for p in pipeline_artifacts]
        ]

    def get_pipeline_context(self, pipeline):
        """Get pipeline context.

        Args:
          pipeline:

        Returns:

        """
        # We rebuild context for ml metadata here.
        run_context = self.store.get_context_by_type_and_name(
            type_name=self.run_type_name, context_name=pipeline.pipeline_name
        )
        if run_context is None:
            raise DoesNotExistException(
                name=pipeline.pipeline_name,
                reason="The pipeline does not exist in metadata store "
                "because it has not been run yet. Please run the "
                "pipeline before trying to fetch artifacts.",
            )
        return run_context
