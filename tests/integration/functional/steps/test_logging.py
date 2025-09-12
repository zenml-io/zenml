import os
import time
from unittest.mock import patch

from zenml import pipeline, step
from zenml.artifacts.utils import _load_file_from_artifact_store
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

_LOGS_STORAGE_MAX_QUEUE_SIZE = 5


@step(enable_cache=False)
def steps_writing_above_the_count_limit(multi=2):
    """A step that writes logs above the count limit."""
    for i in range(_LOGS_STORAGE_MAX_QUEUE_SIZE * multi):
        logger.info(f"step 1 - {i}")
        time.sleep(0.01)


@step(enable_cache=False)
def step_writing_above_the_time_limit():
    """A step that writes logs above the time limit."""
    for i in range(_LOGS_STORAGE_MAX_QUEUE_SIZE):
        logger.info(f"step 1 - {i}")
        time.sleep(0.01)


@patch(
    "zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig.IS_IMMUTABLE_FILESYSTEM",
    True,
)
def test_that_write_buffer_called_multiple_times_on_exceeding_limits():
    """Test that the write buffer is called multiple times on exceeding limits."""

    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit()

    @pipeline
    def _inner_2():
        step_writing_above_the_time_limit()

    with patch(
        "zenml.logging.step_logging.LOGS_STORAGE_MAX_QUEUE_SIZE",
        _LOGS_STORAGE_MAX_QUEUE_SIZE,
    ):
        with patch(
            "zenml.logging.step_logging.PipelineLogsStorage.write_buffer"
        ) as mock_write_buffer:
            run_1 = _inner_1()
            assert mock_write_buffer.call_count > 1

        Client().delete_pipeline(run_1.pipeline.id)

        with patch(
            "zenml.logging.step_logging.PipelineLogsStorage.write_buffer"
        ) as mock_write_buffer:
            with patch(
                "zenml.logging.step_logging.LOGS_WRITE_INTERVAL_SECONDS",
                0.001,
            ):
                run_2 = _inner_2()
                assert mock_write_buffer.call_count > 1
        Client().delete_pipeline(run_2.pipeline.id)


@patch(
    "zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig.IS_IMMUTABLE_FILESYSTEM",
    True,
)
def test_that_small_files_are_merged_together():
    """Test that small files are merged together."""

    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit(multi=10)

    with patch(
        "zenml.logging.step_logging.LOGS_STORAGE_MAX_QUEUE_SIZE",
        _LOGS_STORAGE_MAX_QUEUE_SIZE,
    ):
        ret = _inner_1()  # this run will produce 2+ logs files as it go, proven by previous test

    artifact_store = Client().active_stack.artifact_store
    files = artifact_store.listdir(
        ret.steps["steps_writing_above_the_count_limit"].logs.uri
    )
    assert len(files) == 1
    content = str(
        _load_file_from_artifact_store(
            os.path.join(
                ret.steps["steps_writing_above_the_count_limit"].logs.uri,
                files[0],
            ),
            artifact_store,
            mode="r",
        )
    ).split("\n")

    content_pointer = 0
    for i in range(_LOGS_STORAGE_MAX_QUEUE_SIZE * 10):
        while f"step 1 - {i}" not in content[content_pointer]:
            content_pointer += 1

    Client().delete_pipeline(ret.pipeline.id)
