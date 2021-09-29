from tfx.dsl.components.common.importer import Importer
from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


@orchestrator_store_factory.register(OrchestratorTypes.local)
class LocalOrchestrator(BaseOrchestrator):
    def run(self, zenml_pipeline, **pipeline_args):
        runner = LocalDagRunner()

        # Resolve the importers for external artifact inputs
        importers = {}
        for name, artifact in zenml_pipeline.inputs.items():
            importers[name] = Importer(
                source_uri=artifact.uri, artifact_type=artifact.type
            ).with_id(name)

        import_artifacts = {
            n: i.outputs["result"] for n, i in importers.items()
        }

        # Establish the connections between the components
        zenml_pipeline.connect(**import_artifacts, **zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = list(importers.values()) + [
            s.component for s in zenml_pipeline.steps.values()
        ]

        artifact_store = zenml_pipeline.stack.artifact_store
        metadata_store = zenml_pipeline.stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name="pipeline_name",
            components=steps,
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=False,
        )
        return runner.run(created_pipeline)
