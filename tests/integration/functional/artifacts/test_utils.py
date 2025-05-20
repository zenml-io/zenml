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
    log_metadata,
    pipeline,
    save_artifact,
    step,
)
from zenml.artifacts.utils import register_artifact
from zenml.client import Client
from zenml.enums import ArtifactSaveType
from zenml.models.v2.core.artifact import ArtifactResponse


def test_save_load_artifact_outside_run(clean_client: "Client") -> None:
    """Tests `save_artifact` and `load_artifact` outside of a pipeline run.

    This test verifies:
    - Saving a new artifact and loading it.
    - Saving a new version for an existing artifact and loading both the latest
      and the specific older version.
    - Saving an artifact with a custom version string and loading it.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """
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
    """A ZenML step that manually saves an artifact using `save_artifact`.

    Args:
        value: The value to save as an artifact.
        name: The name to give to the saved artifact.
        version: Optional custom version string for the artifact.
    """
    save_artifact(value, name=name, version=version)


@step
def manual_artifact_loading_step(
    expected_value: int, name: str, version: Optional[str] = None
) -> None:
    """A ZenML step that manually loads an artifact using `load_artifact` and asserts its value.

    Args:
        expected_value: The expected value of the loaded artifact.
        name: The name of the artifact to load.
        version: Optional specific version of the artifact to load.
    """
    loaded_value = load_artifact(name, version)
    assert loaded_value == expected_value


def test_save_load_artifact_in_run(clean_client: "Client") -> None:
    """Tests `save_artifact` and `load_artifact` within pipeline run contexts.

    This test defines two inner pipelines:
    - `_save_load_pipeline`: Saves an artifact in one step and loads it in another.
    - `_load_pipeline`: Loads an artifact (presumably saved by a previous run).

    It then executes these pipelines with various combinations of artifact names,
    versions, and values to ensure correct behavior of saving and loading
    within and across pipeline runs.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

    @pipeline
    def _save_load_pipeline(
        value: int,
        expected_value: int,
        saving_name: str,
        loading_name: str,
        saving_version: Optional[str] = None,
        loading_version: Optional[str] = None,
    ) -> None:
        """Pipeline to test saving and loading an artifact in sequence.

        Args:
            value: Value to save in the first step.
            expected_value: Expected value when loading in the second step.
            saving_name: Name of the artifact to save.
            loading_name: Name of the artifact to load.
            saving_version: Optional version for saving.
            loading_version: Optional version for loading.
        """
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
    def _load_pipeline(expected_value: int, name: str, version: Optional[str]) -> None:
        """Pipeline to test loading an artifact.

        Args:
            expected_value: Expected value of the loaded artifact.
            name: Name of the artifact to load.
            version: Specific version of the artifact to load.
        """
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


def test_log_metadata_existing(clean_client: "Client") -> None:
    """Tests logging metadata to already existing artifacts using `log_metadata`.

    This test verifies that metadata can be added to artifact versions that
    have been previously saved using `save_artifact`. It checks:
    - Logging metadata by providing `artifact_version_id`.
    - Logging metadata by providing `artifact_name` and `artifact_version`.
    - Logging various data types (float, int, str, list of str, list of float)
      as metadata and verifying their retrieval.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """
    av = save_artifact(42, "meaning_of_life")
    log_metadata(
        metadata={"description": "Aria is great!"},
        artifact_version_id=av.id,
    )
    save_artifact(43, "meaning_of_life", version="43")
    log_metadata(
        metadata={"description_2": "Blupus is great!"},
        artifact_name="meaning_of_life",
        artifact_version="43",
    )
    log_metadata(
        metadata={"description_3": "Axl is great!"},
        artifact_name="meaning_of_life",
        artifact_version="1",
    )
    log_metadata(
        metadata={
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
    """A ZenML step that logs metadata for its output artifact using `log_artifact_metadata`.

    Returns:
        A string value ("42") which becomes the artifact's data.
    """
    output_metadata = {
        "description": "Aria is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_artifact_metadata(metadata=output_metadata)
    return "42"


def test_log_metadata_single_output(clean_client: "Client") -> None:
    """Tests logging metadata via `log_artifact_metadata` in a step with a single output.

    This test defines a pipeline with a single step (`artifact_metadata_logging_step`)
    that logs metadata for its output. It then verifies that the logged metadata
    is correctly associated with the output artifact of that step.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

    @pipeline
    def _artifact_metadata_logging_pipeline_single_output() -> None:
        """Pipeline for testing metadata logging for a single output step."""
        artifact_metadata_logging_step()

    _artifact_metadata_logging_pipeline_single_output()
    run_ = _artifact_metadata_logging_pipeline_single_output.model.last_run
    output = run_.steps["artifact_metadata_logging_step"].output
    assert "description" in output.run_metadata
    assert output.run_metadata["description"] == "Aria is great!"
    assert "metrics" in output.run_metadata
    assert output.run_metadata["metrics"] == {"accuracy": 0.9}


@step
def artifact_multi_output_metadata_logging_step() -> Tuple[
    Annotated[str, "str_output"], Annotated[int, "int_output"]
]:
    """A ZenML step with multiple named outputs that logs metadata for one of them.

    This step returns two artifacts, "str_output" and "int_output". It uses
    `log_metadata` to log metadata specifically for the "int_output" artifact.

    Returns:
        A tuple containing a string ("42") and an integer (42).
    """
    output_metadata = {
        "description": "Blupus is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_metadata(
        metadata=output_metadata,
        artifact_name="int_output",
        infer_artifact=True,
    )
    return "42", 42


def test_log_metadata_multi_output(clean_client: "Client") -> None:
    """Tests logging metadata via `log_metadata` in a step with multiple outputs.

    This test defines a pipeline with a step (`artifact_multi_output_metadata_logging_step`)
    that has two named outputs. Metadata is logged explicitly for one of these
    outputs ("int_output"). The test verifies that the metadata is associated
    only with the specified output and not the other.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

    @pipeline
    def _artifact_metadata_logging_pipeline_multi_output() -> None:
        """Pipeline for testing metadata logging for a multi-output step."""
        artifact_multi_output_metadata_logging_step()

    _artifact_metadata_logging_pipeline_multi_output()
    run_ = _artifact_metadata_logging_pipeline_multi_output.model.last_run
    step_ = run_.steps["artifact_multi_output_metadata_logging_step"]
    str_output = step_.outputs["str_output"][0]
    assert "description" not in str_output.run_metadata
    assert "metrics" not in str_output.run_metadata
    int_output = step_.outputs["int_output"][0]
    assert "description" in int_output.run_metadata
    assert int_output.run_metadata["description"] == "Blupus is great!"
    assert "metrics" in int_output.run_metadata
    assert int_output.run_metadata["metrics"] == {"accuracy": 0.9}


@step
def wrong_artifact_multi_output_metadata_logging_step() -> Tuple[
    Annotated[str, "str_output"], Annotated[int, "int_output"]
]:
    """A ZenML step with multiple outputs designed to test error handling of `log_artifact_metadata`.

    This step attempts to use `log_artifact_metadata` without specifying which
    of its multiple outputs the metadata should be applied to. This is expected
    to cause an error.

    Returns:
        A tuple containing a string ("42") and an integer (42).
    """
    output_metadata = {
        "description": "Axl is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_artifact_metadata(output_metadata)
    return "42", 42


def test_log_metadata_raises_error_if_output_name_unclear(
    clean_client: "Client",
) -> None:
    """Tests that `log_artifact_metadata` raises a ValueError in a multi-output step if the target artifact is not specified.

    When a step has multiple outputs, `log_artifact_metadata` (which is a
    shortcut for `log_metadata` with `infer_artifact=True`) cannot determine
    which output the metadata should be associated with unless explicitly told.
    This test verifies that such a situation correctly raises a ValueError.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

    @pipeline
    def _error_test_pipeline() -> None:
        """Pipeline designed to trigger an error in metadata logging."""
        wrong_artifact_multi_output_metadata_logging_step()

    with pytest.raises(ValueError):
        _error_test_pipeline()


def test_download_artifact_files_from_response(
    tmp_path: Path, clean_client_with_run: "Client"
) -> None:
    """Tests the `download_files` method of an `ArtifactVersionResponse`.

    This test retrieves an artifact version from a completed pipeline run,
    downloads its contents to a temporary zip file, extracts the contents,
    and verifies the data.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        clean_client_with_run: A ZenML client instance with a pre-existing
            pipeline run.
    """
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
    tmp_path: Path, clean_client_with_run: "Client"
) -> None:
    """Tests that `download_files` fails if the target file exists and `overwrite` is False.

    This test ensures that the `download_files` method of an
    `ArtifactVersionResponse` does not overwrite an existing file by default,
    raising a `FileExistsError`. It also verifies that setting `overwrite=True`
    allows the download to proceed.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        clean_client_with_run: A ZenML client instance with a pre-existing
            pipeline run.
    """
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


def parallel_artifact_version_creation(mocked_client: "MockedClient") -> int:
    """Helper function for `test_parallel_artifact_creation`.

    Saves an artifact using `save_artifact` with a mocked ZenML client and
    logger to count debug log calls, indicating if a new version was created
    or an existing one was reused (due to race conditions if locking fails).

    Args:
        mocked_client: An instance of the `MockedClient`.

    Returns:
        The number of times the debug logger was called, which implies
        how many version conflict checks occurred.
    """
    with patch("zenml.artifacts.utils.Client", return_value=mocked_client):
        with patch("zenml.artifacts.utils.logger.debug") as logger_mock:
            save_artifact(42, "meaning_of_life")
            return logger_mock.call_count


class MockedClient(Client):
    """A specialized ZenML Client mock for testing parallel artifact creation.

    This class inherits from `zenml.client.Client` and overrides the
    `active_stack` property. Its primary purpose is to allow testing of
    concurrent artifact saving (`save_artifact`) by bypassing potential issues
    related to source resolution (`source_utils`) that might occur in a
    multiprocessing context with the standard client.

    Attributes:
        a_s: The artifact store component to be used by this mocked client.
    """

    def __init__(self, a_s: "StackComponentResponse") -> None:
        """Initializes the MockedClient.

        Args:
            a_s: The artifact store stack component response to associate with
                 this client's active stack.
        """
        self.a_s = a_s
        super().__init__()

    @property
    def active_stack(self) -> "StackResponse":
        """Returns the active stack for this mocked client.

        Returns:
            The active stack response, configured with the artifact store
            provided during initialization.
        """
        return self.a_s


def test_parallel_artifact_creation(clean_client: Client) -> None:
    """Tests that concurrent calls to `save_artifact` create distinct artifact versions.

    This test simulates multiple processes calling `save_artifact` for the
    same artifact name concurrently. It uses a multiprocessing pool and a
    mocked ZenML client to achieve this. The test verifies that the number
    of created artifact versions matches the number of processes, indicating
    that the internal locking mechanism for artifact versioning is working
    correctly.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """
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
        artifact="meaning_of_life", size=min(1000, process_count * 10)
    )
    assert len(avs) == process_count
    assert {av.version for av in avs} == {
        str(i) for i in range(1, process_count + 1)
    }


def test_register_artifact(clean_client: Client) -> None:
    """Tests registering a local folder as a ZenML artifact using `register_artifact`.

    This test creates a local folder with a file, registers the folder as an
    artifact, and then verifies:
    - The artifact version is created with the correct URI and `PREEXISTING` save type.
    - The artifact can be loaded, and its contents match the original file.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

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
    assert artifact.save_type == ArtifactSaveType.PREEXISTING

    loaded_dir = artifact.load()
    assert isinstance(loaded_dir, Path)

    with open(loaded_dir / "test.txt", "r") as f:
        assert f.read() == "test"


def test_register_artifact_out_of_bounds(clean_client: Client) -> None:
    """Tests that `register_artifact` fails if the provided URI is outside the artifact store's path.

    This test attempts to register a temporary directory (which is outside the
    configured artifact store's path) as an artifact. It expects a
    `FileNotFoundError` because the artifact store should not be able to
    reference files outside its designated root.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

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
    """A ZenML step that registers both a folder and a file as artifacts.

    It creates a folder "test_folder" with a "test.txt" file inside the
    artifact store's path. It then calls `register_artifact` for the folder
    and for the file "test.txt" individually.
    """
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
    """A ZenML step that consumes a folder artifact registered in a previous step.

    This step receives a `Path` object pointing to the contents of the
    "test_folder" artifact. It verifies the content of "test.txt" within that
    folder. It also asserts that the input path is a temporary local copy and
    not the original artifact store path. Additionally, it loads and verifies
    the "test_file" artifact.

    Args:
        inp_folder: A Path object representing the loaded "test_folder" artifact.
    """
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


def test_register_artifact_between_steps(clean_client: Client) -> None:
    """Tests using `register_artifact` in one step and consuming the registered artifact in a subsequent step.

    This test defines a pipeline where `register_artifact_step_1` registers
    a folder artifact named "test_folder". `register_artifact_step_2` then
    consumes this artifact by loading it via `client.get_artifact_version()`
    and verifies its content.

    Args:
        clean_client: A ZenML client instance with a clean environment.
    """

    @pipeline(enable_cache=False)
    def _register_artifact_pipeline() -> None:
        """Pipeline to test registering and consuming artifacts between steps."""
        register_artifact_step_1()
        register_artifact_step_2(
            clean_client.get_artifact_version(
                name_id_or_prefix="test_folder", version=1
            ),
            after=["register_artifact_step_1"],
        )

    _register_artifact_pipeline()

[end of tests/integration/functional/artifacts/test_utils.py]
