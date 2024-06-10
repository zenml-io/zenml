import os
import time
from pathlib import Path
from unittest.mock import patch

from zenml import pipeline, step
from zenml.artifacts.utils import _load_file_from_artifact_store
from zenml.client import Client
from zenml.logger import get_logger
from zenml.logging.step_logging import fetch_logs

logger = get_logger(__name__)

_STEP_LOGS_STORAGE_MAX_MESSAGES = 5


@step(enable_cache=False)
def steps_writing_above_the_count_limit(multi=2):
    for i in range(_STEP_LOGS_STORAGE_MAX_MESSAGES * multi):
        logger.info(f"step 1 - {i}")
        time.sleep(0.01)


@step(enable_cache=False)
def step_writing_above_the_time_limit():
    for i in range(_STEP_LOGS_STORAGE_MAX_MESSAGES):
        logger.info(f"step 1 - {i}")
        time.sleep(0.01)


@patch(
    "zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig.IS_IMMUTABLE_FILESYSTEM",
    True,
)
def test_that_save_to_file_called_multiple_times_on_exceeding_limits():
    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit()

    @pipeline
    def _inner_2():
        step_writing_above_the_time_limit()

    with patch(
        "zenml.logging.step_logging.STEP_LOGS_STORAGE_MAX_MESSAGES",
        _STEP_LOGS_STORAGE_MAX_MESSAGES,
    ):
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


@patch(
    "zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig.IS_IMMUTABLE_FILESYSTEM",
    True,
)
def test_that_small_files_are_merged_together():
    @pipeline
    def _inner_1():
        steps_writing_above_the_count_limit(multi=10)

    with patch(
        "zenml.logging.step_logging.STEP_LOGS_STORAGE_MAX_MESSAGES",
        _STEP_LOGS_STORAGE_MAX_MESSAGES,
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
    for i in range(_STEP_LOGS_STORAGE_MAX_MESSAGES * 10):
        while f"step 1 - {i}" not in content[content_pointer]:
            content_pointer += 1

    Client().delete_pipeline(ret.pipeline.id)


def test_that_fetch_logs_works_with_multiple_files(clean_client: Client):
    """Create multiple files in the artifact store and fetch them in different combinations."""
    artifact_store = clean_client.active_stack.artifact_store
    zen_store = clean_client.zen_store
    data_lens = [10, 20, 12, 14]
    data = [str(i) * dl for i, dl in enumerate(data_lens)]
    logs_dir = Path(os.path.join(artifact_store.path, "fake_logs"))
    artifact_store.makedirs(logs_dir)
    logs_dir = str(logs_dir.absolute())
    for i, d in enumerate(data):
        with artifact_store.open(
            os.path.join(logs_dir, f"fake_logs_{i}.txt"), "w"
        ) as f:
            f.write(d)

    # read data from each file separately using offset and length
    for i in range(len(data)):
        data_ = fetch_logs(
            zen_store,
            artifact_store.id,
            logs_dir,
            0 + sum(data_lens[:i]),
            data_lens[i],
        )
        assert data_ == data[i]

    # read data on intersection of 2 files using offset and length
    data_ = fetch_logs(
        zen_store,
        artifact_store.id,
        logs_dir,
        data_lens[0] // 2,
        (data_lens[0] + data_lens[1]) // 2,
    )
    assert data_.count(data[0][0]) == data_lens[0] // 2
    assert data_.count(data[1][0]) == data_lens[1] // 2

    # read data from all files using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_dir)
    for i, d in enumerate(data):
        assert data_.count(d[0]) == data_lens[i]

    # read data from last file using negative offset
    data_ = fetch_logs(
        zen_store, artifact_store.id, logs_dir, -data_lens[-1], data_lens[-1]
    )
    assert data_ == data[-1]

    # read data from files overlap using negative offset
    data_ = fetch_logs(
        zen_store,
        artifact_store.id,
        logs_dir,
        -data_lens[-1] - data_lens[-2] - (data_lens[-3] // 2),
        (data_lens[-2] // 2) + (data_lens[-3] // 2),
    )
    assert data_.count(data[-3][0]) == data_lens[-3] // 2
    assert data_.count(data[-2][0]) == data_lens[-2] // 2


def test_that_fetch_logs_works_with_one_file(clean_client: Client):
    """Create only one log file in folder and try to offset through it."""
    artifact_store = clean_client.active_stack.artifact_store
    zen_store = clean_client.zen_store
    data = "111222333"
    logs_dir = Path(os.path.join(artifact_store.path, "fake_logs"))
    artifact_store.makedirs(logs_dir)
    logs_dir = str(logs_dir.absolute())
    with artifact_store.open(
        os.path.join(logs_dir, "fake_logs.txt"), "w"
    ) as f:
        f.write(data)

    # read data only 1s using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_dir, 0, 3)
    assert data_.count("1") == 3

    # read data only 3s using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_dir, 6, 3)
    assert data_.count("3") == 3

    # read data from all files using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_dir, 0, len(data))
    assert data_.count("1") == 3
    assert data_.count("2") == 3
    assert data_.count("3") == 3

    # read data from last file using negative offset
    data_ = fetch_logs(zen_store, artifact_store.id, logs_dir, -3, 3)
    assert data_ == "333"


def test_that_fetch_logs_works_with_legacy(clean_client: Client):
    """Create only one log file, pass it directly and try to offset through it."""
    artifact_store = clean_client.active_stack.artifact_store
    zen_store = clean_client.zen_store
    data = "111222333"
    logs_dir = Path(os.path.join(artifact_store.path, "fake_logs"))
    artifact_store.makedirs(logs_dir)
    logs_file = str((logs_dir / "fake_logs.log").absolute())
    with artifact_store.open(logs_file, "w") as f:
        f.write(data)

    # read data only 1s using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_file, 0, 3)
    assert data_.count("1") == 3

    # read data only 3s using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_file, 6, 3)
    assert data_.count("3") == 3

    # read data from all files using offset and length
    data_ = fetch_logs(zen_store, artifact_store.id, logs_file, 0, len(data))
    assert data_.count("1") == 3
    assert data_.count("2") == 3
    assert data_.count("3") == 3
