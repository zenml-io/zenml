from zenml.zen_stores.schemas import PipelineRunSchema


def handle_run_status_update(
    pipeline_run: PipelineRunSchema,
):
    """Helper function - checks dispatcher state and sends run status update.

    Args:
        pipeline_run: A PipelineRunSchema object.
    """
    from zenml.zen_server.utils import (
        event_dispatcher,
        is_event_dispatcher_initialized,
    )

    if is_event_dispatcher_initialized():
        event_dispatcher().handle_run_status_update(pipeline_run)
