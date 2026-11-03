#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Offline execution tests for the AWS artifact-store setup script."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional, Tuple

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "infra/scripts/aws-artifact-store-setup.sh"
)

HARNESS = r"""
set -e
# All commands are shell functions, so no installed cloud CLI can be reached.
export PATH=''
record_call() {
    printf '%s\0' "$@" >> "$CALL_LOG"
    printf '\0' >> "$CALL_LOG"
}
aws() {
    record_call aws "$@"
    case "$1 $2" in
        'sts get-caller-identity')
            if [ "$FAIL_STS" = '1' ]; then
                printf 'Authentication failed\n' >&2
                return 255
            fi
            printf '123456789012\n'
            ;;
        's3api create-bucket')
            for argument in "$@"; do
                if [ "$argument" = 'LocationConstraint=us-east-1' ]; then
                    printf 'InvalidLocationConstraint\n' >&2
                    return 255
                fi
            done
            ;;
        'iam create-access-key')
            printf '{"AccessKey":{"AccessKeyId":"test-access-key","SecretAccessKey":"test-secret"}}\n'
            ;;
    esac
}
jq() {
    case "$2" in
        .AccessKey.AccessKeyId) printf 'test-access-key\n' ;;
        .AccessKey.SecretAccessKey) printf 'test-secret\n' ;;
        *) return 1 ;;
    esac
}
zenml() { record_call zenml "$@"; }
sleep() { :; }
cat() {
    while IFS= read -r line || [ -n "$line" ]; do
        printf '%s\n' "$line"
    done
}
if [ -n "$MISSING_DEPENDENCY" ]; then
    unset -f "$MISSING_DEPENDENCY"
fi
source "$SETUP_SCRIPT"
"""

RunScript = Callable[
    [Optional[str], str, bool],
    Tuple[subprocess.CompletedProcess[str], list[list[str]]],
]


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> None:
    """These shell-only tests do not use a configured ZenML store."""


@pytest.fixture(scope="module", autouse=True)
def check_module_requirements() -> None:
    """The harness supplies every external command used by the script."""


@pytest.fixture
def run_script(tmp_path: Path) -> RunScript:
    """Build a command-isolated Bash harness.

    Args:
        tmp_path: Temporary directory for the copied script and call log.

    Returns:
        A runner returning the process result and captured command arguments.
    """
    if os.name == "nt":
        bash = (
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Git/bin/bash.exe"
        )
        if not bash.is_file():
            pytest.skip("Git Bash is required on Windows")
        bash_path = str(bash)
    else:
        bash_path = shutil.which("bash") or ""
        if not bash_path:
            pytest.skip("Bash is required")

    script = tmp_path / "setup.sh"
    script.write_text(SCRIPT.read_text(), encoding="utf-8", newline="\n")
    harness = tmp_path / "harness.sh"
    harness.write_text(HARNESS, encoding="utf-8", newline="\n")
    call_log = tmp_path / "calls"

    def run(
        region: Optional[str] = "eu-central-1",
        missing: str = "",
        fail_sts: bool = False,
    ) -> Tuple[subprocess.CompletedProcess[str], list[list[str]]]:
        """Execute the real script using shell functions instead of cloud tools.

        Args:
            region: Region override, or None to use the script's default.
            missing: Command to remove from the isolated environment.
            fail_sts: Whether authentication should fail.

        Returns:
            The process result and captured argument lists.
        """
        environment = {
            key: os.environ[key]
            for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
            if key in os.environ
        }
        environment.update(
            SETUP_SCRIPT=script.as_posix(),
            CALL_LOG=call_log.as_posix(),
            NAME="zenml-test",
            RANDOM_SUFFIX="fixedsfx",
            FAIL_STS="1" if fail_sts else "0",
            MISSING_DEPENDENCY=missing,
        )
        if region is not None:
            environment["REGION"] = region
        call_log.write_bytes(b"")
        result = subprocess.run(
            [bash_path, "--noprofile", "--norc", harness.as_posix()],
            env=environment,
            text=True,
            capture_output=True,
            timeout=15,
        )
        calls = [
            record.decode("utf-8").split("\0")
            for record in call_log.read_bytes().split(b"\0\0")
            if record
        ]
        return result, calls

    return run


@pytest.mark.parametrize("region", ["us-east-1", "eu-west-1", None])
def test_bucket_region_and_stack_registration(
    run_script: RunScript, region: Optional[str]
) -> None:
    """Use the AWS region contract and preserve registration and cleanup."""
    result, calls = run_script(region, "", False)

    assert result.returncode == 0, result.stderr
    bucket = next(
        call for call in calls if call[:3] == ["aws", "s3api", "create-bucket"]
    )
    expected_region = region or "eu-central-1"
    assert bucket[:7] == [
        "aws",
        "s3api",
        "create-bucket",
        "--bucket",
        "zenml-test-fixedsfx",
        "--region",
        expected_region,
    ]
    assert bucket[7:] == (
        []
        if expected_region == "us-east-1"
        else [
            "--create-bucket-configuration",
            f"LocationConstraint={expected_region}",
        ]
    )
    assert [call[:3] for call in calls if call[0] == "zenml"] == [
        ["zenml", "service-connector", "register"],
        ["zenml", "artifact-store", "register"],
        ["zenml", "stack", "register"],
    ]
    connector = next(
        call for call in calls if call[:2] == ["zenml", "service-connector"]
    )
    assert "--aws_access_key_id=test-access-key" in connector
    assert "--aws_secret_access_key=test-secret" in connector
    assert "--access-key-id test-access-key" in result.stdout


@pytest.mark.parametrize("missing", ["aws", "jq", "zenml"])
def test_missing_dependency_stops_before_aws_calls(
    run_script: RunScript, missing: str
) -> None:
    """Fail before creating resources or credentials when a tool is absent."""
    result, calls = run_script("eu-central-1", missing, False)

    assert result.returncode != 0
    assert calls == []
    assert missing in result.stderr
    assert "required" in result.stderr.lower()


def test_authentication_failure_stops_before_resource_creation(
    run_script: RunScript,
) -> None:
    """Keep an authentication failure free of resource mutations."""
    result, calls = run_script("eu-central-1", "", True)

    assert result.returncode != 0
    assert "credentials" in result.stderr.lower()
    assert [call[:3] for call in calls] == [
        ["aws", "sts", "get-caller-identity"]
    ]
