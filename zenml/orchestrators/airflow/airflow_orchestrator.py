from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


@orchestrator_store_factory.register(OrchestratorTypes.airflow)
class AirflowOrchestrator(BaseOrchestrator):
    def run(self, pipeline):
        # DEBUG # TODO: to be removed
        from zenml.stacks.local_stack import LocalStack

        stack = LocalStack()

        runner = LocalDagRunner()

        importers = {}
        for name, artifact in zenml_pipeline.__inputs.items():
            importers[name] = Importer(
                source_uri=artifact.uri, artifact_type=artifact.type
            ).with_id(name)

        import_artifacts = {
            n: i.outputs["result"] for n, i in importers.items()
        }

        # Establish the connections between the components
        zenml_pipeline.connect(**import_artifacts, **zenml_pipeline.__steps)

        # Create the final step list and the corresponding pipeline
        steps = list(importers.values()) + [
            s.get_component() for s in zenml_pipeline.__steps.values()
        ]

        artifact_store = stack.artifact_store
        metadata_store = stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name="pipeline_name",
            components=steps,
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=pipeline_args["enable_cache"],
        )
        runner.run(created_pipeline)
