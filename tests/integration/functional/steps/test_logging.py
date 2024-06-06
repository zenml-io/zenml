import os
from unittest.mock import patch

from zenml import pipeline, step
from zenml.artifacts.utils import _load_file_from_artifact_store
from zenml.client import Client
from zenml.logger import get_logger
from zenml.logging import (
    STEP_LOGS_STORAGE_MAX_MESSAGES,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def steps_writing_above_the_count_limit(multi=2):
    for i in range(STEP_LOGS_STORAGE_MAX_MESSAGES * multi):
        logger.info(f"step 1 - {i}")


@step(enable_cache=False)
def step_writing_above_the_time_limit():
    for i in range(STEP_LOGS_STORAGE_MAX_MESSAGES):
        logger.info(f"step 1 - {i}")


def test_that_save_to_file_called_multiple_times_on_exceeding_limits():
    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit()

    @pipeline
    def _inner_2():
        step_writing_above_the_time_limit()

    with patch(
        "zenml.logging.step_logging.StepLogsStorage.save_to_file"
    ) as mock_save_to_file:
        run_1 = _inner_1()
        assert mock_save_to_file.call_count > 1

    Client().delete_pipeline(run_1.pipeline.id)

    with patch(
        "zenml.logging.step_logging.StepLogsStorage.save_to_file"
    ) as mock_save_to_file:
        with patch(
            "zenml.logging.step_logging.STEP_LOGS_STORAGE_INTERVAL_SECONDS",
            0.001,
        ):
            run_2 = _inner_2()
            assert mock_save_to_file.call_count > 1
    Client().delete_pipeline(run_2.pipeline.id)


def test_that_small_files_are_merged_together():
    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit(multi=10)

    ret = (
        _inner_1()
    )  # this run will produce 2+ logs files as it go, proven by previous test

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
    for i in range(STEP_LOGS_STORAGE_MAX_MESSAGES * 10):
        while f"step 1 - {i}" not in content[content_pointer]:
            content_pointer += 1

    Client().delete_pipeline(ret.pipeline.id)
