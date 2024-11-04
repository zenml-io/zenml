"""Integration tests for artifact util functions."""

import multiprocessing
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from unittest.mock import patch

import pytest
from typing_extensions import Annotated

from zenml import (
    load_artifact,
    log_artifact_metadata,
    pipeline,
    save_artifact,
    step,
)
from zenml.artifacts.utils import register_artifact
from zenml.client import Client
from zenml.models.v2.core.artifact import ArtifactResponse


def test_save_load_artifact_outside_run(clean_client):
    """Test artifact saving and loading outside of runs."""
    save_artifact(42, "meaning_of_life")
    assert load_artifact("meaning_of_life") == 42

    save_artifact(43, "meaning_of_life")
    assert load_artifact("meaning_of_life") == 43
    assert load_artifact("meaning_of_life", version="1") == 42

    save_artifact(44, "meaning_of_life", version="44")
    assert load_artifact("meaning_of_life") == 44
    assert load_artifact("meaning_of_life", version="44") == 44


@step
def manual_artifact_saving_step(
    value: int, name: str, version: Optional[str] = None
) -> None:
    """A step that logs an artifact."""
    save_artifact(value, name=name, version=version)


@step
def manual_artifact_loading_step(
    expected_value: int, name: str, version: Optional[str] = None
) -> None:
    """A step that loads an artifact."""
    loaded_value = load_artifact(name, version)
    assert loaded_value == expected_value


def test_save_load_artifact_in_run(clean_client):
    """Test artifact saving and loading inside runs."""

    @pipeline
    def _save_load_pipeline(
        value: int,
        expected_value: int,
        saving_name: str,
        loading_name: str,
        saving_version: Optional[str] = None,
        loading_version: Optional[str] = None,
    ):
        manual_artifact_saving_step(
            value=value, name=saving_name, version=saving_version
        )
        manual_artifact_loading_step(
            expected_value=expected_value,
            name=loading_name,
            version=loading_version,
            after="manual_artifact_saving_step",
        )

    @pipeline
    def _load_pipeline(expected_value, name, version):
        manual_artifact_loading_step(
            expected_value=expected_value, name=name, version=version
        )

    _save_load_pipeline(
        value=42,
        saving_name="meaning_of_life",
        loading_name="meaning_of_life",
        expected_value=42,
    )

    _save_load_pipeline(
        value=43,
        saving_name="meaning_of_life",
        loading_name="meaning_of_life",
        expected_value=43,
    )

    _load_pipeline(
        expected_value=42,
        name="meaning_of_life",
        version="1",
    )

    _save_load_pipeline(
        value=44,
        saving_name="meaning_of_life",
        loading_name="meaning_of_life",
        saving_version="44",
        loading_version="2",
        expected_value=43,
    )

    _load_pipeline(
        expected_value=44,
        name="meaning_of_life",
        version="44",
    )


def test_log_artifact_metadata_existing(clean_client):
    """Test logging artifact metadata for existing artifacts."""
    save_artifact(42, "meaning_of_life")
    log_artifact_metadata(
        {"description": "Aria is great!"}, artifact_name="meaning_of_life"
    )
    save_artifact(43, "meaning_of_life", version="43")
    log_artifact_metadata(
        {"description_2": "Blupus is great!"}, artifact_name="meaning_of_life"
    )
    log_artifact_metadata(
        {"description_3": "Axl is great!"},
        artifact_name="meaning_of_life",
        artifact_version="1",
    )
    log_artifact_metadata(
        {
            "float": 1.0,
            "int": 1,
            "str": "1.0",
            "list_str": ["1.0", "2.0"],
            "list_floats": [1.0, 2.0],
        },
        artifact_name="meaning_of_life",
        artifact_version="1",
    )

    artifact_1 = clean_client.get_artifact_version(
        "meaning_of_life", version="1"
    )
    assert "description" in artifact_1.run_metadata
    assert artifact_1.run_metadata["description"] == "Aria is great!"
    assert "description_3" in artifact_1.run_metadata
    assert artifact_1.run_metadata["description_3"] == "Axl is great!"
    assert "float" in artifact_1.run_metadata
    assert artifact_1.run_metadata["float"] - 1.0 < 10e-6
    assert "int" in artifact_1.run_metadata
    assert artifact_1.run_metadata["int"] == 1
    assert "str" in artifact_1.run_metadata
    assert artifact_1.run_metadata["str"] == "1.0"
    assert "list_str" in artifact_1.run_metadata
    assert len(set(artifact_1.run_metadata["list_str"]) - {"1.0", "2.0"}) == 0
    assert "list_floats" in artifact_1.run_metadata
    for each in artifact_1.run_metadata["list_floats"]:
        if 0.99 < each < 1.01:
            assert each - 1.0 < 10e-6
        else:
            assert each - 2.0 < 10e-6

    artifact_2 = clean_client.get_artifact_version(
        "meaning_of_life", version="43"
    )
    assert "description_2" in artifact_2.run_metadata
    assert artifact_2.run_metadata["description_2"] == "Blupus is great!"


@step
def artifact_metadata_logging_step() -> str:
    """A step that logs artifact metadata."""
    output_metadata = {
        "description": "Aria is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_artifact_metadata(output_metadata)
    return "42"


def test_log_artifact_metadata_single_output(clean_client):
    """Test logging artifact metadata for a single output."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        artifact_metadata_logging_step()

    artifact_metadata_logging_pipeline()
    run_ = artifact_metadata_logging_pipeline.model.last_run
    output = run_.steps["artifact_metadata_logging_step"].output
    assert "description" in output.run_metadata
    assert output.run_metadata["description"] == "Aria is great!"
    assert "metrics" in output.run_metadata
    assert output.run_metadata["metrics"] == {"accuracy": 0.9}


@step
def artifact_multi_output_metadata_logging_step() -> (
    Tuple[Annotated[str, "str_output"], Annotated[int, "int_output"]]
):
    """A step that logs artifact metadata and has multiple outputs."""
    output_metadata = {
        "description": "Blupus is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_artifact_metadata(metadata=output_metadata, artifact_name="int_output")
    return "42", 42


def test_log_artifact_metadata_multi_output(clean_client):
    """Test logging artifact metadata for multiple outputs."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        artifact_multi_output_metadata_logging_step()

    artifact_metadata_logging_pipeline()
    run_ = artifact_metadata_logging_pipeline.model.last_run
    step_ = run_.steps["artifact_multi_output_metadata_logging_step"]
    str_output = step_.outputs["str_output"]
    assert "description" not in str_output.run_metadata
    assert "metrics" not in str_output.run_metadata
    int_output = step_.outputs["int_output"]
    assert "description" in int_output.run_metadata
    assert int_output.run_metadata["description"] == "Blupus is great!"
    assert "metrics" in int_output.run_metadata
    assert int_output.run_metadata["metrics"] == {"accuracy": 0.9}


@step
def wrong_artifact_multi_output_metadata_logging_step() -> (
    Tuple[Annotated[str, "str_output"], Annotated[int, "int_output"]]
):
    """A step that logs artifact metadata and has multiple outputs."""
    output_metadata = {
        "description": "Axl is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_artifact_metadata(output_metadata)
    return "42", 42


def test_log_artifact_metadata_raises_error_if_output_name_unclear(
    clean_client,
):
    """Test that `log_artifact_metadata` raises an error if the output name is unclear."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        wrong_artifact_multi_output_metadata_logging_step()

    with pytest.raises(ValueError):
        artifact_metadata_logging_pipeline()


def test_download_artifact_files_from_response(
    tmp_path, clean_client_with_run: "Client"
):
    """Test that we can download artifact files from an artifact version."""
    artifact: ArtifactResponse = clean_client_with_run.get_artifact(
        name_id_or_prefix="connected_two_step_pipeline::constant_int_output_test_step::output"
    )
    artifact_version_id = list(artifact.versions.values())[0].id
    av = clean_client_with_run.get_artifact_version(artifact_version_id)
    # create temporary path ending in .zip

    zipfile_path = os.path.join(tmp_path, "some_file.zip")
    av.download_files(path=zipfile_path)
    assert os.path.exists(zipfile_path)

    # unzip the file at zipfile_path
    with zipfile.ZipFile(zipfile_path, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    with open(os.path.join(tmp_path, "data.json"), "r") as f:
        assert f.read() == "7"

    # clean up
    shutil.rmtree(tmp_path)


def test_download_artifact_files_from_response_fails_if_exists(
    tmp_path, clean_client_with_run
):
    """Test that downloading artifact files from an artifact version fails.

    Failure when the file already exists and `overwrite` is False."""
    artifact: ArtifactResponse = clean_client_with_run.get_artifact(
        name_id_or_prefix="connected_two_step_pipeline::constant_int_output_test_step::output"
    )
    artifact_version_id = list(artifact.versions.values())[0].id
    av = clean_client_with_run.get_artifact_version(artifact_version_id)
    # create temporary path ending in .zip

    zipfile_path = os.path.join(tmp_path, "some_file.zip")
    # create a file at zipfile_path
    with open(zipfile_path, "w") as f:
        f.write("hello aria, blupus and axl")

    # fails if the file already exists
    with pytest.raises(FileExistsError):
        av.download_files(path=zipfile_path)

    # it works with overwrite parameter
    av.download_files(path=zipfile_path, overwrite=True)
    assert os.path.exists(zipfile_path)

    # unzip the file at zipfile_path
    with zipfile.ZipFile(zipfile_path, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    with open(os.path.join(tmp_path, "data.json"), "r") as f:
        assert f.read() == "7"
    # clean up
    shutil.rmtree(tmp_path)


def parallel_artifact_version_creation(mocked_client) -> int:
    with patch("zenml.artifacts.utils.Client", return_value=mocked_client):
        with patch("zenml.artifacts.utils.logger.debug") as logger_mock:
            save_artifact(42, "meaning_of_life")
            return logger_mock.call_count


class MockedClient(Client):
    """Mocked client for testing parallel artifact creation.

    Only goal: avoid source problems from `source_utils`.
    """

    def __init__(self, a_s) -> None:
        self.a_s = a_s
        super().__init__()

    @property
    def active_stack(self):
        return self.a_s


def test_parallel_artifact_creation(clean_client: Client):
    """Test that artifact version creation can be parallelized."""
    process_count = 20
    args = [MockedClient(clean_client.active_stack)] * process_count
    with multiprocessing.get_context("spawn").Pool(5) as pool:
        results = pool.map(
            parallel_artifact_version_creation,
            iterable=args,
        )

    assert sum(results), (
        "Test was not parallel. "
        "Consider increasing the number of processes or pools."
    )

    avs = clean_client.list_artifact_versions(
        name="meaning_of_life", size=min(1000, process_count * 10)
    )
    assert len(avs) == process_count
    assert {av.version for av in avs} == {
        str(i) for i in range(1, process_count + 1)
    }


def test_register_artifact(clean_client: Client):
    """Tests that a folder can be linked as an artifact in local setting."""

    uri_prefix = os.path.join(
        clean_client.active_stack.artifact_store.path, "test_folder"
    )
    os.makedirs(uri_prefix, exist_ok=True)
    with open(os.path.join(uri_prefix, "test.txt"), "w") as f:
        f.write("test")

    register_artifact(folder_or_file_uri=uri_prefix, name="test_folder")

    artifact = clean_client.get_artifact_version(
        name_id_or_prefix="test_folder", version=1
    )
    assert artifact
    assert artifact.uri == uri_prefix

    loaded_dir = artifact.load()
    assert isinstance(loaded_dir, Path)

    with open(loaded_dir / "test.txt", "r") as f:
        assert f.read() == "test"


def test_register_artifact_out_of_bounds(clean_client: Client):
    """Tests that a folder cannot be linked as an artifact if out of bounds."""

    uri_prefix = tempfile.mkdtemp()
    try:
        with pytest.raises(FileNotFoundError):
            register_artifact(
                folder_or_file_uri=uri_prefix, name="test_folder"
            )
    finally:
        os.rmdir(uri_prefix)


@step(enable_cache=False)
def register_artifact_step_1() -> None:
    # find out where to save some data
    uri_prefix = os.path.join(
        Client().active_stack.artifact_store.path, "test_folder"
    )
    os.makedirs(uri_prefix, exist_ok=True)
    # generate dat to validate in register_artifact_step_2
    test_file = os.path.join(uri_prefix, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    register_artifact(folder_or_file_uri=uri_prefix, name="test_folder")

    register_artifact(folder_or_file_uri=test_file, name="test_file")


@step(enable_cache=False)
def register_artifact_step_2(
    inp_folder: Path,
) -> None:
    # step should receive a path pointing to the folder
    # from register_artifact_step_1
    with open(inp_folder / "test.txt", "r") as f:
        assert f.read() == "test"
    # at the same time the input artifact is no longer inside the
    # artifact store, but in the temporary folder of local file system
    assert not str(inp_folder.absolute()).startswith(
        Client().active_stack.artifact_store.path
    )

    file_artifact_path = Client().get_artifact_version("test_file").load()

    with open(file_artifact_path, "r") as f:
        assert f.read() == "test"


def test_register_artifact_between_steps(clean_client: Client):
    """Tests that a folder can be linked as an artifact and used in pipelines."""

    @pipeline(enable_cache=False)
    def register_artifact_pipeline():
        register_artifact_step_1()
        register_artifact_step_2(
            clean_client.get_artifact_version(
                name_id_or_prefix="test_folder", version=1
            ),
            after=["register_artifact_step_1"],
        )

    register_artifact_pipeline()
