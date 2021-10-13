from typing import TYPE_CHECKING

from tfx.orchestration import pipeline as tfx_pipeline
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.steps.base_step import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


@orchestrator_store_factory.register(OrchestratorTypes.local)
class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    def run(self, zenml_pipeline: "BasePipeline", **pipeline_args):
        """Runs a pipeline locally.

        Args:
            zenml_pipeline: The pipeline to run.
            **pipeline_args: Unused kwargs to conform with base signature.
        """
        runner = LocalDagRunner()

        # Establish the connections between the components
        assert all(
            issubclass(type(s), BaseStep) for s in zenml_pipeline.steps.values()
        ), (
            "When you are designing a pipeline, you can only pass in @step "
            "like annotated objects."
        )
        zenml_pipeline.connect(**zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = [s.component for s in zenml_pipeline.steps.values()]

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
