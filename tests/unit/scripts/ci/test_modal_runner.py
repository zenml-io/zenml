"""Unit tests for the Modal fast CI runner helpers."""

import threading
import time
from pathlib import Path

from scripts.ci.modal_runner import (
    BATCH_MANIFESTS_DIRNAME,
    JUNIT_LOG_END,
    JUNIT_LOG_START,
    RUNNER_COMMAND,
    RUNNER_EXIT_INFRA_FAILURE,
    RUNNER_EXIT_TEST_FAILURE,
    BatchExecution,
    BatchResult,
    PreparedGitSourceSnapshot,
    ScheduledBatch,
    StartupSummary,
    SuiteConfig,
    _allocate_fixed_suite_parallelism,
    _allocate_suite_parallelism,
    _allocate_weighted_suite_parallelism,
    _batch_manifest_path,
    _build_batch_environment,
    _collect_node_ids_locally,
    _count_duration_matches,
    _execute_queued_batches,
    _extract_embedded_junit,
    _finalize_batch,
    _git_sparse_checkout_paths,
    _load_cached_node_ids,
    _node_id_cache_path,
    _normalize_git_remote_url,
    _parse_collected_node_ids,
    _queue_batch_count,
    _resolve_git_source_ref,
    _save_cached_node_ids,
    _write_batch_manifest,
    create_batch_failure_junit,
    extract_failed_node_ids,
    extract_failure_details,
    extract_test_durations,
    format_failure_console_report,
    merge_junit_xml_documents,
    parse_args,
    write_duration_cache,
    write_failure_report,
    write_summary,
)


def test_parse_args_supports_multiple_suites() -> None:
    """CLI parsing should accept multiple suites in one invocation."""
    args = parse_args(["--suite", "unit", "--suite", "integration"])

    assert args.suite == ["unit", "integration"]
    assert args.python_version == "3.13"
    assert args.max_sandboxes == 20
    assert args.sandbox_cpu == 4.0
    assert args.sandbox_memory_mb == 8192
    assert args.unit_pytest_dist == "worksteal"
    assert args.unit_max_sandboxes is None
    assert args.collect_coverage is True


def test_parse_args_can_disable_coverage_collection() -> None:
    """CLI parsing should allow coverage to be disabled for speed tests."""
    args = parse_args(["--suite", "unit", "--no-collect-coverage"])

    assert args.collect_coverage is False


def test_parse_args_can_override_unit_pytest_distribution() -> None:
    """CLI parsing should expose the unit xdist distribution mode."""
    args = parse_args(["--suite", "unit", "--unit-pytest-dist", "loadscope"])

    assert args.unit_pytest_dist == "loadscope"


def test_normalize_git_remote_url_converts_ssh_to_https() -> None:
    """Git SSH remotes should be converted into HTTPS URLs for Modal."""
    assert (
        _normalize_git_remote_url("git@github.com:zenml-io/core.git")
        == "https://github.com/zenml-io/core.git"
    )
    assert (
        _normalize_git_remote_url("ssh://git@github.com/zenml-io/core.git")
        == "https://github.com/zenml-io/core.git"
    )


def test_git_sparse_checkout_paths_keep_fast_ci_runtime_inputs() -> None:
    """Sparse checkout should include runtime inputs and skip bulky repo areas."""
    paths = _git_sparse_checkout_paths()

    assert "src" in paths
    assert "tests" in paths
    assert "scripts" in paths
    assert "examples" in paths
    assert "templates" in paths
    assert "pyproject.toml" in paths
    assert "docs" not in paths


def test_resolve_git_source_ref_requires_clean_pushed_head(monkeypatch) -> None:
    """Strict git mode should reject dirty or unpushed work before Modal work."""
    responses = {
        ("status", "--porcelain"): "",
        ("rev-parse", "HEAD"): "abc123\n",
        ("remote", "get-url", "origin"): "git@github.com:zenml-io/core.git\n",
        ("fetch", "--quiet", "origin"): "",
        (
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            "abc123",
            "refs/remotes/origin",
        ): "refs/remotes/origin/develop\n",
    }

    def fake_run(cmd, **kwargs):
        key = tuple(cmd[1:])
        stdout = responses[key]
        return type("Result", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    source_ref = _resolve_git_source_ref()

    assert source_ref.commit_sha == "abc123"
    assert source_ref.remote_url == "https://github.com/zenml-io/core.git"
    assert len(source_ref.cache_namespace) == 16


def test_allocate_suite_parallelism_splits_budget_evenly() -> None:
    """Global suite parallelism should be split evenly when possible."""
    assert _allocate_suite_parallelism(
        suite_count=2, total_parallelism=20
    ) == [
        10,
        10,
    ]


def test_allocate_suite_parallelism_distributes_remainder() -> None:
    """Any leftover sandbox budget should be distributed deterministically."""
    assert _allocate_suite_parallelism(
        suite_count=2, total_parallelism=21
    ) == [
        11,
        10,
    ]


def test_allocate_weighted_suite_parallelism_favors_heavier_suite() -> None:
    """A heavier suite should receive a larger share of the sandbox budget."""
    assert _allocate_weighted_suite_parallelism(
        suite_names=["unit", "integration"],
        estimated_total_durations=[2363.0, 4681.0],
        total_parallelism=20,
        unit_max_sandboxes=None,
    ) == [7, 13]


def test_allocate_weighted_suite_parallelism_falls_back_when_all_zero() -> (
    None
):
    """Zero-duration suites should use the even split fallback."""
    assert _allocate_weighted_suite_parallelism(
        suite_names=["unit", "integration"],
        estimated_total_durations=[0.0, 0.0],
        total_parallelism=5,
        unit_max_sandboxes=None,
    ) == [3, 2]


def test_allocate_weighted_suite_parallelism_caps_unit_suite() -> None:
    """Unit+integration runs should reserve only the configured unit budget."""
    assert _allocate_weighted_suite_parallelism(
        suite_names=["unit", "integration"],
        estimated_total_durations=[2363.0, 4681.0],
        total_parallelism=20,
        unit_max_sandboxes=3,
    ) == [3, 17]


def test_allocate_fixed_suite_parallelism_reserves_one_for_unit() -> None:
    """Unit should get one sandbox and integration should get the remainder."""
    assert _allocate_fixed_suite_parallelism(
        suite_names=["unit", "integration"],
        total_parallelism=20,
        unit_max_sandboxes=1,
    ) == [1, 19]


def test_queue_batch_count_matches_parallelism() -> None:
    """Batch count should equal parallelism to avoid queuing overhead."""
    assert (
        _queue_batch_count(
            suite=SuiteConfig(
                name="integration",
                test_environment="default",
                default_duration=5.0,
                batch_timeout=900,
            ),
            suite_parallelism=4,
            node_ids=[
                f"tests/integration/test_{index}.py::test_ok"
                for index in range(30)
            ],
        )
        == 4
    )


def test_queue_batch_count_caps_at_test_count() -> None:
    """Batch count should not exceed the number of tests."""
    assert (
        _queue_batch_count(
            suite=SuiteConfig(
                name="unit",
                test_environment="default",
                default_duration=0.5,
                batch_timeout=900,
                pytest_workers=4,
            ),
            suite_parallelism=3,
            node_ids=[
                f"tests/unit/test_{index}.py::test_ok" for index in range(2)
            ],
        )
        == 2
    )


def test_create_batch_failure_junit_contains_exit_code() -> None:
    """Synthetic JUnit should preserve the sandbox exit code."""
    junit_xml = create_batch_failure_junit(
        batch_name="unit-batch-01",
        node_ids=["tests/unit/test_sample.py::test_failure"],
        exit_code=124,
        message="Sandbox timed out.",
    )

    assert "Sandbox exited with code 124." in junit_xml
    assert 'testsuite name="unit-batch-01"' in junit_xml


def test_extract_failed_node_ids_reads_failures() -> None:
    """Failed testcases should be converted back into node IDs."""
    junit_xml = """
    <testsuite name="unit">
      <testcase classname="tests.unit.test_file" name="test_ok" />
      <testcase classname="tests.unit.test_file" name="test_fail">
        <failure message="boom" />
      </testcase>
      <testcase classname="tests.unit.test_other" name="test_error">
        <error message="kaput" />
      </testcase>
    </testsuite>
    """

    assert extract_failed_node_ids(junit_xml) == [
        "tests/unit/test_file.py::test_fail",
        "tests/unit/test_other.py::test_error",
    ]


def test_extract_test_durations_reads_pytest_junit_timings() -> None:
    """Per-test timings should be extracted from pytest JUnit output."""
    junit_xml = """
    <testsuite name="unit">
      <testcase classname="tests.unit.test_file" name="test_ok" time="1.25" />
      <testcase classname="tests.unit.test_file.TestClass" name="test_method" time="2.5" />
      <testcase classname="modal" name="batch-infrastructure" time="4.0" />
    </testsuite>
    """

    assert extract_test_durations(junit_xml) == {
        "tests/unit/test_file.py::test_ok": 1.25,
        "tests/unit/test_file.py::TestClass::test_method": 2.5,
    }


def test_extract_failure_details_reads_failure_summary() -> None:
    """Failure details should capture node IDs and a concise summary."""
    junit_xml = """
    <testsuite name="unit">
      <testcase classname="tests.unit.test_file" name="test_fail">
        <failure message="ValueError: boom" />
      </testcase>
    </testsuite>
    """

    details = extract_failure_details(junit_xml, batch_name="unit-batch-01")

    assert len(details) == 1
    assert details[0].node_id == "tests/unit/test_file.py::test_fail"
    assert details[0].kind == "ValueError"
    assert details[0].summary == "ValueError: boom"


def test_merge_junit_xml_documents_wraps_in_testsuites() -> None:
    """Merged JUnit output should contain one outer testsuites tag."""
    merged = merge_junit_xml_documents(
        [
            '<testsuite name="unit-a"><testcase classname="a" name="one" /></testsuite>',
            '<testsuite name="unit-b"><testcase classname="b" name="two" /></testsuite>',
        ],
        suite_name="unit",
    )

    assert merged.startswith("<testsuites")
    assert 'name="unit-a"' in merged
    assert 'name="unit-b"' in merged


def test_write_summary_lists_failed_tests(tmp_path: Path) -> None:
    """The markdown summary should include failing tests and timings."""
    summary_path = tmp_path / "summary.md"
    summary = write_summary(
        results=[
            BatchResult(
                suite="unit",
                batch_name="unit-batch-01",
                node_ids=["a"],
                expected_duration=1.0,
                runtime_seconds=2.0,
                exit_code=0,
                junit_xml="<testsuite />",
                failed_node_ids=[],
                log_output="",
                coverage_path=None,
            ),
            BatchResult(
                suite="integration",
                batch_name="integration-batch-01",
                node_ids=["b"],
                expected_duration=5.0,
                runtime_seconds=6.0,
                exit_code=1,
                junit_xml=(
                    '<testsuite><testcase classname="tests.integration.test_file" '
                    'name="test_fail"><failure message="ValueError: boom" />'
                    "</testcase></testsuite>"
                ),
                failed_node_ids=["tests.integration.test_file::test_fail"],
                log_output="boom",
                coverage_path=None,
            ),
        ],
        output_path=summary_path,
        startup_summary=StartupSummary(
            dependency_cache_hit=True,
            source_snapshot_cache_hit=True,
            node_id_cache_hits={"unit": False, "integration": True},
            launch_to_first_batch_seconds=12.5,
        ),
    )

    assert summary_path.exists()
    assert "Failed batches: 1" in summary
    assert "Dependency image cache: hit" in summary
    assert "Git source snapshot cache: hit" in summary
    assert "Launch to first batch: 12.5s" in summary
    assert "`tests.integration.test_file::test_fail`" in summary
    assert "## Failure Groups" in summary
    assert "Representative message: `ValueError: boom`" in summary


def test_write_failure_report_groups_causes(tmp_path: Path) -> None:
    """The failure report should group failures by their cause."""
    output_path = tmp_path / "failures.md"

    written_path = write_failure_report(
        results=[
            BatchResult(
                suite="unit",
                batch_name="unit-batch-01",
                node_ids=["tests/unit/test_file.py::test_fail"],
                expected_duration=1.0,
                runtime_seconds=2.0,
                exit_code=1,
                junit_xml=(
                    '<testsuite><testcase classname="tests.unit.test_file" '
                    'name="test_fail"><failure message="ValueError: boom" />'
                    "</testcase></testsuite>"
                ),
                failed_node_ids=["tests/unit/test_file.py::test_fail"],
                log_output="",
                coverage_path=None,
            ),
        ],
        output_path=output_path,
    )

    assert written_path == output_path
    report = output_path.read_text(encoding="utf-8")
    assert "## Failure Groups" in report
    assert "### `ValueError` (1 failure)" in report
    assert "Cause: `ValueError: boom`" in report


def test_format_failure_console_report_is_concise() -> None:
    """Console failure output should show compact batch/test summaries."""
    report = format_failure_console_report(
        [
            BatchResult(
                suite="unit",
                batch_name="unit-batch-01",
                node_ids=["tests/unit/test_file.py::test_fail"],
                expected_duration=1.0,
                runtime_seconds=2.0,
                exit_code=1,
                junit_xml=(
                    '<testsuite><testcase classname="tests.unit.test_file" '
                    'name="test_fail"><failure message="ValueError: boom" />'
                    "</testcase></testsuite>"
                ),
                failed_node_ids=["tests/unit/test_file.py::test_fail"],
                log_output="very long log",
                coverage_path=None,
            )
        ]
    )

    assert "Failure summary:" in report
    assert "`unit-batch-01`" in report
    assert "`ValueError: boom`" in report


def test_write_duration_cache_merges_existing_and_new_results(
    tmp_path: Path,
) -> None:
    """Successful batches should update the local duration cache."""
    output_path = tmp_path / "test_durations.json"

    written_path = write_duration_cache(
        results=[
            BatchResult(
                suite="unit",
                batch_name="unit-batch-01",
                node_ids=["tests/unit/test_file.py::test_ok"],
                expected_duration=1.0,
                runtime_seconds=2.0,
                exit_code=0,
                junit_xml=(
                    '<testsuite><testcase classname="tests.unit.test_file" '
                    'name="test_ok" time="1.5" /></testsuite>'
                ),
                failed_node_ids=[],
                log_output="",
                coverage_path=None,
            ),
            BatchResult(
                suite="unit",
                batch_name="unit-batch-02",
                node_ids=["tests/unit/test_file.py::test_fail"],
                expected_duration=1.0,
                runtime_seconds=2.0,
                exit_code=1,
                junit_xml="<testsuite />",
                failed_node_ids=["tests/unit/test_file.py::test_fail"],
                log_output="",
                coverage_path=None,
            ),
        ],
        existing_durations={"tests/unit/test_existing.py::test_old": 3.0},
        output_path=output_path,
    )

    assert written_path == output_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "tests/unit/test_existing.py::test_old": 3.0,\n'
        '  "tests/unit/test_file.py::test_ok": 1.5\n'
        "}"
    )


def test_runner_exit_codes_are_stable() -> None:
    """Runner exit codes should remain stable for workflow integration."""
    assert RUNNER_EXIT_TEST_FAILURE == 1
    assert RUNNER_EXIT_INFRA_FAILURE == 2


def test_parse_collected_node_ids_ignores_warning_lines() -> None:
    """Collector output should ignore warning file references."""
    output = """
    tests/unit/services/test_service.py::test_from_model
    tests/unit/services/test_service.py:30
    tests/unit/steps/test_utils.py::test_thing
    """

    assert _parse_collected_node_ids(output) == [
        "tests/unit/services/test_service.py::test_from_model",
        "tests/unit/steps/test_utils.py::test_thing",
    ]


def test_runner_command_does_not_pass_entire_suite_path_to_pytest() -> None:
    """Each batch should run only its scheduled node IDs."""
    assert '"tests/${suite}"' not in RUNNER_COMMAND


def test_runner_command_decodes_node_ids_from_env_var_when_present() -> None:
    """Sandboxes should decode node IDs from ZENML_NODE_IDS_B64 to skip upload."""
    assert 'if [[ -n "${ZENML_NODE_IDS_B64:-}" ]]; then' in RUNNER_COMMAND
    assert (
        'echo "$ZENML_NODE_IDS_B64" | base64 -d > "${ZENML_NODE_ID_PATH}"'
        in RUNNER_COMMAND
    )


def test_runner_command_falls_back_to_polling_without_env_var() -> None:
    """The sandbox should still poll for the file when the env var is absent."""
    assert 'if [[ ! -s "${ZENML_NODE_ID_PATH}" ]]; then' in RUNNER_COMMAND
    assert 'mapfile -t NODE_IDS < "${ZENML_NODE_ID_PATH}"' in RUNNER_COMMAND


def test_runner_command_can_skip_coverage_collection() -> None:
    """Coverage flags should be guarded behind an env-controlled switch."""
    assert (
        'if [[ "${ZENML_COLLECT_COVERAGE:-1}" == "1" ]]; then'
        in RUNNER_COMMAND
    )


def test_runner_command_uses_configured_xdist_distribution() -> None:
    """The runner should read the xdist distribution strategy from env."""
    assert "ZENML_PYTEST_DIST:-worksteal" in RUNNER_COMMAND


def test_runner_command_accepts_optional_import_mode() -> None:
    """Modal shards should be able to opt into pytest importlib mode."""
    assert (
        'if [[ -n "${ZENML_PYTEST_IMPORT_MODE:-}" ]]; then' in RUNNER_COMMAND
    )
    assert '--import-mode "${ZENML_PYTEST_IMPORT_MODE}"' in RUNNER_COMMAND


def test_runner_command_emits_heartbeat_for_long_running_batches() -> None:
    """Long-running shards should emit periodic logs while pytest is active."""
    assert "[heartbeat]" in RUNNER_COMMAND
    assert "pytest still running for" in RUNNER_COMMAND


def test_runner_command_embeds_junit_in_stdout() -> None:
    """Batch stdout should include JUnit markers for reliable artifact recovery."""
    assert 'echo "${ZENML_JUNIT_START}"' in RUNNER_COMMAND
    assert 'echo "${ZENML_JUNIT_END}"' in RUNNER_COMMAND


def test_build_batch_environment_targets_snapshot_and_tmp_runtime() -> None:
    """Sandboxes should run from the git snapshot with writable state in /tmp."""
    env = _build_batch_environment(
        suite=SuiteConfig(
            name="unit",
            test_environment="default",
            default_duration=0.5,
            batch_timeout=900,
        ),
        batch_name="unit-batch-01",
        source_snapshot=PreparedGitSourceSnapshot(
            volume=object(),
            snapshot_path="/mnt/zenml-fast-ci/repo-snapshots/ns/abc123",
            cache_hit=True,
            commit_sha="abc123",
        ),
    )

    assert (
        env["ZENML_BATCH_REPOSITORY_PATH"]
        == "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123"
    )
    assert env["PYTHONPATH"] == (
        "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123:"
        "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123/src"
    )
    assert env["ZENML_CONFIG_PATH"] == "/tmp/zenml-fast-ci/config"
    assert env["ZENML_LOCAL_STORES_PATH"] == "/tmp/zenml-fast-ci/local-stores"


def test_extract_embedded_junit_returns_xml_and_cleaned_logs() -> None:
    """Embedded JUnit payloads should be decoded and stripped from logs."""
    junit_xml = (
        '<testsuite name="unit"><testcase name="test_ok" /></testsuite>'
    )
    payload = (
        "before\n"
        f"{JUNIT_LOG_START}\n"
        "PHRlc3RzdWl0ZSBuYW1lPSJ1bml0Ij48dGVzdGNhc2UgbmFtZT0idGVzdF9vayIgLz48L3Rlc3RzdWl0ZT4=\n"
        f"{JUNIT_LOG_END}\n"
        "after\n"
    )

    extracted, cleaned = _extract_embedded_junit(payload)

    assert extracted == junit_xml
    assert cleaned == "before\nafter"


def test_count_duration_matches_counts_known_node_ids() -> None:
    """Duration coverage should count only matched tests."""
    assert (
        _count_duration_matches(
            ["a", "b", "c"],
            {"a": 1.0, "c": 2.0},
        )
        == 2
    )


def test_collect_node_ids_locally_returns_node_ids_on_success(
    monkeypatch,
) -> None:
    """Local collection should parse and return node IDs on a zero exit."""
    import subprocess

    fake_output = (
        "tests/unit/test_foo.py::test_bar\ntests/unit/test_foo.py::test_baz\n"
    )

    def fake_run(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode=0)
        result.stdout = fake_output
        result.stderr = ""
        return result

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    node_ids = _collect_node_ids_locally(
        suite="unit",
        test_environment="default",
        pytest_import_mode=None,
    )

    assert node_ids == [
        "tests/unit/test_foo.py::test_bar",
        "tests/unit/test_foo.py::test_baz",
    ]


def test_collect_node_ids_locally_returns_none_on_fatal_exit(
    monkeypatch,
) -> None:
    """Fatal exit codes (not 0/2/5) should return None so the caller can raise."""
    import subprocess

    def fake_run(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode=1)
        result.stdout = ""
        result.stderr = "usage error"
        return result

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    node_ids = _collect_node_ids_locally(
        suite="unit",
        test_environment="default",
        pytest_import_mode=None,
    )

    assert node_ids is None


def test_collect_node_ids_locally_returns_partial_results_on_import_errors(
    monkeypatch,
) -> None:
    """Exit code 1 (import errors) should still return any collected node IDs."""
    import subprocess

    fake_output = (
        "tests/integration/test_foo.py::test_bar\n"
        "tests/integration/test_baz.py::test_qux\n"
    )

    def fake_run(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode=1)
        result.stdout = fake_output
        result.stderr = (
            "ERROR collecting tests/integration/test_needs_boto3.py"
        )
        return result

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    node_ids = _collect_node_ids_locally(
        suite="integration",
        test_environment="default",
        pytest_import_mode=None,
    )

    assert node_ids == [
        "tests/integration/test_foo.py::test_bar",
        "tests/integration/test_baz.py::test_qux",
    ]


def test_collect_node_ids_locally_returns_none_on_timeout(monkeypatch) -> None:
    """Timeouts during local collection should be treated as a fallback signal."""
    import subprocess

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=120)

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    node_ids = _collect_node_ids_locally(
        suite="unit",
        test_environment="default",
        pytest_import_mode=None,
    )

    assert node_ids is None


def test_collect_node_ids_locally_uses_continue_on_collection_errors(
    monkeypatch,
) -> None:
    """Local collection must pass --continue-on-collection-errors to handle partial imports."""
    import subprocess

    captured_cmd: list[str] = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        result = subprocess.CompletedProcess(cmd, returncode=0)
        result.stdout = "tests/unit/test_foo.py::test_bar\n"
        result.stderr = ""
        return result

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    _collect_node_ids_locally(
        suite="unit",
        test_environment="default",
        pytest_import_mode=None,
    )

    assert "--continue-on-collection-errors" in captured_cmd


def test_collect_node_ids_locally_includes_import_mode_flag(
    monkeypatch,
) -> None:
    """Local collection should forward --import-mode when specified."""
    import subprocess

    captured_cmd: list[str] = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        result = subprocess.CompletedProcess(cmd, returncode=0)
        result.stdout = "tests/unit/test_foo.py::test_bar\n"
        result.stderr = ""
        return result

    monkeypatch.setattr("scripts.ci.modal_runner.subprocess.run", fake_run)

    _collect_node_ids_locally(
        suite="unit",
        test_environment="default",
        pytest_import_mode="importlib",
    )

    assert "--import-mode=importlib" in captured_cmd


def test_node_id_cache_round_trip(tmp_path: Path, monkeypatch) -> None:
    """Collected node IDs should be cached per suite and fingerprint."""
    monkeypatch.setattr(
        "scripts.ci.modal_runner.DEFAULT_NODE_ID_CACHE_DIR",
        tmp_path / "node-ids",
    )
    written_path = _save_cached_node_ids(
        suite="unit",
        collection_fingerprint="fingerprint",
        pytest_import_mode="importlib",
        node_ids=["tests/unit/test_file.py::test_ok"],
    )

    assert written_path == _node_id_cache_path(
        suite="unit",
        collection_fingerprint="fingerprint",
        pytest_import_mode="importlib",
    )
    assert _load_cached_node_ids(
        suite="unit",
        collection_fingerprint="fingerprint",
        pytest_import_mode="importlib",
    ) == ["tests/unit/test_file.py::test_ok"]


def test_write_batch_manifest_persists_node_ids(tmp_path: Path) -> None:
    """Scheduled batches should be inspectable after launch or timeout."""
    manifest_path = _write_batch_manifest(
        artifacts_dir=tmp_path,
        batch_name="integration-batch-16",
        suite_name="integration",
        batch=ScheduledBatch(
            node_ids=(
                "tests/integration/test_a.py::test_one",
                "tests/integration/test_b.py::test_two",
            ),
            duration_seconds=68.5,
        ),
    )

    assert manifest_path == _batch_manifest_path(
        artifacts_dir=tmp_path,
        batch_name="integration-batch-16",
    )
    assert manifest_path.parent.name == BATCH_MANIFESTS_DIRNAME
    payload = manifest_path.read_text(encoding="utf-8")
    assert '"suite": "integration"' in payload
    assert '"node_count": 2' in payload
    assert "tests/integration/test_a.py::test_one" in payload


def test_execute_queued_batches_respects_parallelism_and_completes_all(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Queued dispatch should run each batch once within the live budget."""
    created_sandboxes: list[str] = []
    current_outstanding = 0
    peak_outstanding = 0
    lock = threading.Lock()

    captured_envs: list[dict] = []

    class FakeSandbox:
        def __init__(self, name: str) -> None:
            self._name = name
            self.returncode = 0

        def wait(self) -> None:
            time.sleep(0.01)

        def terminate(self) -> None:
            pass

    async def fake_create_aio(*args, **kwargs):
        nonlocal current_outstanding, peak_outstanding
        name = kwargs.get("name", "unknown")
        captured_envs.append(kwargs.get("env", {}))
        with lock:
            current_outstanding += 1
            peak_outstanding = max(peak_outstanding, current_outstanding)
            created_sandboxes.append(name)
        return FakeSandbox(name)

    def fake_finalize(execution):
        nonlocal current_outstanding
        time.sleep(0.01)
        with lock:
            current_outstanding -= 1
        return BatchResult(
            suite="integration",
            batch_name=execution.batch_name,
            node_ids=list(execution.scheduled_batch.node_ids),
            expected_duration=1.0,
            runtime_seconds=1.0,
            exit_code=0,
            junit_xml="<testsuite />",
            failed_node_ids=[],
            log_output="",
            coverage_path=None,
        )

    monkeypatch.setattr(
        "scripts.ci.modal_runner._finalize_batch",
        fake_finalize,
    )

    import modal

    monkeypatch.setattr(
        modal.Sandbox.create,
        "aio",
        fake_create_aio,
    )

    results = _execute_queued_batches(
        app=None,
        image=None,
        source_snapshot=PreparedGitSourceSnapshot(
            volume=object(),
            snapshot_path="/mnt/zenml-fast-ci/repo-snapshots/ns/abc123",
            cache_hit=True,
            commit_sha="abc123",
        ),
        suite=SuiteConfig(
            name="integration",
            test_environment="default",
            default_duration=5.0,
            batch_timeout=900,
        ),
        batches=[
            ScheduledBatch(
                node_ids=(f"tests/integration/test_{index}.py::test_ok",),
                duration_seconds=1.0,
            )
            for index in range(1, 7)
        ],
        suite_dir=tmp_path,
        max_parallelism=2,
        sandbox_cpu=4.0,
        sandbox_memory_mb=8192,
    )

    import base64

    assert [result.batch_name for result in results] == [
        "integration-batch-01",
        "integration-batch-02",
        "integration-batch-03",
        "integration-batch-04",
        "integration-batch-05",
        "integration-batch-06",
    ]
    assert len(created_sandboxes) == 6
    assert peak_outstanding <= 2
    # Node IDs should be embedded in the env, not uploaded after creation.
    for i, env in enumerate(captured_envs):
        assert "ZENML_NODE_IDS_B64" in env
        assert (
            env["PYTHONPATH"]
            == "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123:"
            "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123/src"
        )
        assert (
            env["ZENML_BATCH_REPOSITORY_PATH"]
            == "/mnt/zenml-fast-ci/repo-snapshots/ns/abc123"
        )
        decoded = base64.b64decode(env["ZENML_NODE_IDS_B64"]).decode()
        assert f"tests/integration/test_{i + 1}.py::test_ok" in decoded


def test_finalize_batch_turns_timeout_into_failed_batch(
    tmp_path: Path,
) -> None:
    """Sandbox timeouts should not crash the runner."""

    class SandboxTimeoutError(Exception):
        pass

    class FakeFilesystem:
        def read_text(self, path: str) -> str:
            raise FileNotFoundError(path)

        def read_bytes(self, path: str) -> bytes:
            raise FileNotFoundError(path)

    class FakeSandbox:
        def __init__(self) -> None:
            self.filesystem = FakeFilesystem()
            self.returncode = None

        def wait(self) -> None:
            raise SandboxTimeoutError()

        def terminate(self) -> None:
            return None

    execution = BatchExecution(
        suite=SuiteConfig(
            name="unit",
            test_environment="default",
            default_duration=0.5,
            batch_timeout=360,
        ),
        batch_name="unit-batch-01",
        scheduled_batch=ScheduledBatch(
            node_ids=("tests/unit/test_example.py::test_thing",),
            duration_seconds=1.0,
        ),
        sandbox=FakeSandbox(),
        artifacts_dir=tmp_path,
        start_time=0.0,
    )

    result = _finalize_batch(execution)

    assert result.exit_code == 124
    assert result.failed_node_ids == ["tests/unit/test_example.py::test_thing"]


def test_write_duration_cache_backfills_timeout_batch_durations(
    tmp_path: Path,
) -> None:
    """Timed-out batches should still teach the scheduler a conservative cost."""
    output_path = tmp_path / "test_durations.json"

    written_path = write_duration_cache(
        results=[
            BatchResult(
                suite="integration",
                batch_name="integration-batch-16",
                node_ids=[
                    "tests/integration/test_a.py::test_one",
                    "tests/integration/test_b.py::test_two",
                ],
                expected_duration=68.5,
                runtime_seconds=960.0,
                exit_code=124,
                junit_xml=create_batch_failure_junit(
                    batch_name="integration-batch-16",
                    node_ids=[
                        "tests/integration/test_a.py::test_one",
                        "tests/integration/test_b.py::test_two",
                    ],
                    exit_code=124,
                    message="Modal terminated the sandbox after the batch timeout.",
                ),
                failed_node_ids=[
                    "tests/integration/test_a.py::test_one",
                    "tests/integration/test_b.py::test_two",
                ],
                log_output="",
                coverage_path=None,
            )
        ],
        existing_durations={},
        output_path=output_path,
    )

    assert written_path == output_path
    assert output_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "tests/integration/test_a.py::test_one": 480.0,\n'
        '  "tests/integration/test_b.py::test_two": 480.0\n'
        "}"
    )
