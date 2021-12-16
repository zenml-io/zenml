import time
from typing import Optional

from tfx.orchestration.portable import data_types, launcher

from zenml.exceptions import DuplicateRunNameError
from zenml.logger import get_logger

logger = get_logger(__name__)


def _format_timedelta_pretty(seconds: float) -> str:
    """Format a float representing seconds into a string.

    Args:
        seconds: result of a time.time() - time.time().

    Returns:
        Formatted time string.
    """
    int_seconds = int(seconds)
    days, int_seconds = divmod(int_seconds, 86400)
    hours, int_seconds = divmod(int_seconds, 3600)
    minutes, int_seconds = divmod(int_seconds, 60)
    if days > 0:
        return "%dd%dh%dm%ds" % (days, hours, minutes, int_seconds)
    elif hours > 0:
        return "%dh%dm%ds" % (hours, minutes, int_seconds)
    elif minutes > 0:
        return "%dm%ds" % (minutes, int_seconds)
    else:
        return f"{seconds:.3f}s"


def execute_tfx_component(
    tfx_launcher: launcher.Launcher,
) -> Optional[data_types.ExecutionInfo]:
    """Executes a tfx component.

    Args:
        tfx_launcher: A tfx launcher to execute the component.

    Returns:
        Optional execution info returned by the launcher.
    """
    step_name = tfx_launcher._pipeline_node.node_info.id  # type: ignore[attr-defined] # noqa
    start_time = time.time()
    logger.info(f"Step `{step_name}` has started.")
    try:
        execution_info = tfx_launcher.launch()
    except RuntimeError as e:
        if "execution has already succeeded" in str(e):
            # Hacky workaround to catch the error that a pipeline run with
            # this name already exists. Raise an error with a more descriptive
            # message instead.
            raise DuplicateRunNameError()
        else:
            raise

    run_duration = _format_timedelta_pretty(time.time() - start_time)
    logger.info(f"Step `{step_name}` has finished in {run_duration}.")
    return execution_info
