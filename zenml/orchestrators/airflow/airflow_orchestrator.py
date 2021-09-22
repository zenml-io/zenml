from zenml.enums import OrchestratorTypes
from zenml.orchestrators.airflow.airflow_dag_runner import AirflowDagRunner
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


class AirflowOrchestrator(BaseOrchestrator):
    orchestrator_type: OrchestratorTypes = OrchestratorTypes.airflow

    def run(self, pipeline):
        # DEBUG # TODO: to be removed
        from zenml.providers.local_provider import LocalProvider
        provider = LocalProvider()

        runner = LocalDagRunner()

        importers = {}
        for name, artifact in zenml_pipeline.__inputs.items():
            importers[name] = Importer(source_uri=artifact.uri,
                                       artifact_type=artifact.type
                                       ).with_id(name)

        import_artifacts = {n: i.outputs["result"]
                            for n, i in importers.items()}

        # Establish the connections between the components
        zenml_pipeline.connect(**import_artifacts, **zenml_pipeline.__steps)

        # Create the final step list and the corresponding pipeline
        steps = list(importers.values()) + [s.get_component()
                                            for s in
                                            zenml_pipeline.__steps.values()]

        artifact_store = provider.artifact_store
        metadata_store = provider.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name="pipeline_name",
            components=steps,
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=pipeline_args["enable_cache"],
        )
        runner.run(created_pipeline)