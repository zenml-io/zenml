#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Deterministic tests for the authenticated API fuzz harness."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from tests.fuzz.api_fixtures import (
    ApiCleanupError,
    ApiHarness,
    restore_around_example,
)
from tests.fuzz.api_server import (
    RunningApiServer,
    build_server_command,
    build_server_environment,
    running_api_server,
)
from tests.fuzz.database import DisposableDatabase


def test_server_command_runs_current_source_directly(tmp_path: Path) -> None:
    """The server command uses Uvicorn directly against the checkout."""
    command = build_server_command(port=8123)

    assert command[:3] == [sys.executable, "-m", "uvicorn"]
    assert command[3] == "zenml.zen_server.zen_server_api:app"
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == "8123"


def test_server_environment_is_child_only_and_authenticated(
    tmp_path: Path,
) -> None:
    """Server configuration stays under the run and keeps bearer auth on."""
    target = DisposableDatabase.sqlite(tmp_path / "api.sqlite3", tmp_path)
    original_config = os.environ.get("ZENML_CONFIG_PATH")

    environment = build_server_environment(target, tmp_path)

    assert environment["ZENML_CONFIG_PATH"].startswith(str(tmp_path))
    assert environment["ZENML_LOCAL_STORES_PATH"].startswith(str(tmp_path))
    assert environment["ZENML_STORE_URL"] == target.url
    assert environment["ZENML_SERVER_AUTH_SCHEME"] == (
        "OAUTH2_PASSWORD_BEARER"
    )
    assert environment["ZENML_SERVER_AUTO_ACTIVATE"] == "false"
    assert environment["ZENML_ANALYTICS_OPT_IN"] == "false"
    assert os.environ.get("ZENML_CONFIG_PATH") == original_config


def test_server_environment_normalizes_sqlalchemy_mysql_driver(
    tmp_path: Path,
) -> None:
    """ZenML receives its supported MySQL URL without a driver suffix."""
    target = DisposableDatabase(
        url=(
            "mysql+pymysql://root:test@127.0.0.1:3306/zenml_fuzz_environment"
        ),
        backend="mysql",
        owner=tmp_path,
        database_name="zenml_fuzz_environment",
    )

    environment = build_server_environment(target, tmp_path)

    assert environment["ZENML_STORE_URL"] == (
        "mysql://root:test@127.0.0.1:3306/zenml_fuzz_environment"
    )


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:////tmp/user.sqlite3",
        "mysql://root:secret@localhost/production",
    ],
)
def test_destructive_reset_rejects_non_test_database(
    url: str, tmp_path: Path
) -> None:
    """Cleanup refuses databases that are not owned by this run."""
    target = DisposableDatabase.unsafe_for_test(url=url, owner=tmp_path)

    with pytest.raises(RuntimeError, match="not a disposable fuzz database"):
        target.assert_owned()


def test_cleanup_preserves_original_and_cleanup_failures() -> None:
    """A failed restoration reports both the test and cleanup errors."""
    calls = 0

    def reset() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("cleanup failed")

    with pytest.raises(ApiCleanupError) as error_info:
        with restore_around_example(reset):
            raise AssertionError("original failure")

    assert isinstance(error_info.value.original_error, AssertionError)
    assert str(error_info.value.original_error) == "original failure"
    assert isinstance(error_info.value.cleanup_error, RuntimeError)
    assert str(error_info.value.cleanup_error) == "cleanup failed"


def test_cleanup_failure_quarantines_api_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A harness refuses further requests after baseline restoration fails."""
    server = cast(
        RunningApiServer,
        SimpleNamespace(token="token", base_url="http://127.0.0.1:1"),
    )
    harness = ApiHarness(server)
    calls = 0

    def reset() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("cleanup failed")

    monkeypatch.setattr(harness, "reset_tags", reset)
    with pytest.raises(ApiCleanupError) as error_info:
        with harness.isolated_example():
            pass

    assert error_info.value.original_error is None
    assert str(error_info.value.cleanup_error) == "cleanup failed"
    with pytest.raises(RuntimeError, match="cannot be reused"):
        harness.request("GET", "/api/v1/tags")


def test_sqlite_cleanup_after_server_already_exited(tmp_path: Path) -> None:
    """SQLite cleanup runs when the server process has already stopped."""
    with running_api_server(
        backend="sqlite", output_directory=tmp_path
    ) as server:
        sqlite_path = server.database.sqlite_path
        assert sqlite_path is not None
        assert sqlite_path.exists()
        server.process.terminate()
        server.process.wait(timeout=10)

    assert not sqlite_path.exists()


def test_authenticated_server_seeds_and_restores_baseline(
    tmp_path: Path,
) -> None:
    """A real server rejects anonymous calls and restores logical tag IDs."""
    backend = os.environ.get("ZENML_FUZZ_BACKEND", "sqlite")
    with running_api_server(
        backend=backend, output_directory=tmp_path
    ) as server:
        harness = ApiHarness(server)
        anonymous = harness.anonymous_request("GET", "/api/v1/tags")
        assert anonymous.status_code == 401

        first_baseline = harness.seed_baseline()
        assert first_baseline.project_id
        assert first_baseline.pipeline_id
        assert first_baseline.snapshot_id
        assert first_baseline.run_id
        assert set(first_baseline.tag_ids) == {"primary", "secondary"}
        schema = harness.openapi_schema()
        tag_operations = schema["paths"]["/api/v1/tags"]
        assert {"get", "post"}.issubset(tag_operations)

        pipeline_page = harness.request_json(
            "GET",
            "/api/v1/pipelines",
            params={"project": first_baseline.project_id},
        )
        assert [item["id"] for item in pipeline_page["items"]] == [
            first_baseline.pipeline_id
        ]
        assert pipeline_page["items"][0]["body"]["project_id"] == (
            first_baseline.project_id
        )
        snapshot = harness.request_json(
            "GET", f"/api/v1/pipeline_snapshots/{first_baseline.snapshot_id}"
        )
        assert snapshot["body"]["pipeline_id"] == first_baseline.pipeline_id
        assert snapshot["body"]["project_id"] == first_baseline.project_id
        run = harness.request_json(
            "GET", f"/api/v1/runs/{first_baseline.run_id}"
        )
        assert run["body"]["status"] == "completed"
        assert run["body"]["pipeline_id"] == first_baseline.pipeline_id
        assert run["body"]["project_id"] == first_baseline.project_id
        run_page = harness.request_json(
            "GET",
            "/api/v1/runs",
            params={"project": first_baseline.project_id},
        )
        assert [item["id"] for item in run_page["items"]] == [
            first_baseline.run_id
        ]
        assert harness.list_count("/api/v1/projects") >= 1
        assert harness.list_count("/api/v1/pipelines") >= 1
        assert harness.list_count("/api/v1/runs") >= 1

        with harness.isolated_example() as baseline:
            created = harness.request_json(
                "POST",
                "/api/v1/tags",
                json={"name": "generated", "color": "green"},
                expected_status=200,
            )
            harness.request_json(
                "PUT",
                f"/api/v1/tags/{created['id']}",
                json={"name": "renamed"},
                expected_status=200,
            )
            duplicate = harness.request(
                "POST",
                "/api/v1/tags",
                json={"name": "fuzz-primary", "color": "red"},
            )
            assert duplicate.status_code == 409
            harness.request(
                "DELETE",
                f"/api/v1/tags/{baseline.tag_ids['secondary']}",
                expected_status=200,
            )

        restored = harness.current_baseline()
        assert set(restored.tag_ids) == {"primary", "secondary"}
        assert restored.tag_ids != first_baseline.tag_ids
        assert harness.tag_names() == {"fuzz-primary", "fuzz-secondary"}
        harness.close()
