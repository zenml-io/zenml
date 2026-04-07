"""Unit tests for shared dev requirement export helpers."""

import subprocess
from pathlib import Path

from scripts.install_dev_requirements import (
    build_compile_requirements_command,
    build_editable_project_spec,
    collect_integration_requirements,
    ignored_integrations_for_dev_install,
    write_compiled_requirements,
    write_integration_input_requirements,
)


def test_ignored_integrations_for_dev_install_adds_python_and_os_rules() -> (
    None
):
    """Ignored integrations should include Python and OS-specific skips."""
    linux_313 = ignored_integrations_for_dev_install(
        python_version="3.13",
        target_os="Linux",
    )
    windows_311 = ignored_integrations_for_dev_install(
        python_version="3.11",
        target_os="Windows",
    )

    assert "feast" in linux_313
    assert "tensorflow" in linux_313
    assert "deepchecks" in linux_313
    assert "pytorch" in windows_311
    assert "neural_prophet" in windows_311


def test_build_editable_project_spec_matches_install_format() -> None:
    """The editable install spec should match the shell install command."""
    assert build_editable_project_spec() == (
        ".[server,templates,terraform,secrets-aws,secrets-gcp,"
        "secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,"
        "connectors-aws,connectors-gcp,connectors-azure,azureml,"
        "sagemaker,vertex]"
    )


def test_collect_integration_requirements_dedupes_and_skips_ignored(
    monkeypatch,
) -> None:
    """Integration export should exclude ignored integrations."""

    class FakeNumpyIntegration:
        @classmethod
        def get_requirements(cls, target_os=None, python_version=None):
            return ["numpy<3.0"]

    class FakeTensorflowIntegration:
        @classmethod
        def get_requirements(cls, target_os=None, python_version=None):
            return ["tensorflow>=2.12,<2.15"]

    class FakeScipyIntegration:
        @classmethod
        def get_requirements(cls, target_os=None, python_version=None):
            return ["numpy<3.0", "scipy"]

    class FakeRegistry:
        integrations = {
            "numpy": FakeNumpyIntegration,
            "tensorflow": FakeTensorflowIntegration,
            "scipy": FakeScipyIntegration,
        }

    monkeypatch.setattr(
        "scripts.install_dev_requirements._load_integration_registry",
        lambda root: FakeRegistry(),
    )

    requirements = collect_integration_requirements(
        python_version="3.13",
        target_os="Linux",
    )

    assert requirements == ["numpy<3.0", "scipy"]


def test_write_integration_input_requirements_persists_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Integration input export should include pins and the project spec."""
    monkeypatch.setattr(
        "scripts.install_dev_requirements.collect_integration_requirements",
        lambda **kwargs: ["numpy<3.0", "scipy"],
    )

    output_path = write_integration_input_requirements(
        python_version="3.13",
        target_os="Linux",
        output_path=tmp_path / "requirements.txt",
        include_project_spec=True,
    )

    assert output_path.read_text(encoding="utf-8") == (
        "numpy<3.0\n"
        "scipy\n"
        "pyyaml>=6.0.1\n"
        "pyopenssl\n"
        "typing-extensions\n"
        "maison<2\n"
        ".[server,templates,terraform,secrets-aws,secrets-gcp,"
        "secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,"
        "connectors-aws,connectors-gcp,connectors-azure,azureml,"
        "sagemaker,vertex]\n"
    )


def test_build_compile_requirements_command_targets_requested_platform(
    tmp_path: Path,
) -> None:
    """Compiled export should use uv's target platform flags."""
    integration_input = tmp_path / "integration-input.txt"
    command = build_compile_requirements_command(
        python_version="3.13",
        target_os="Linux",
        target_platform=None,
        output_path=tmp_path / "requirements.txt",
        input_paths=[integration_input],
    )

    assert command[:4] == ["uv", "pip", "compile", "pyproject.toml"]
    assert "--python-version" in command
    assert "--python-platform" in command
    assert command[command.index("--python-version") + 1] == "3.13"
    assert command[command.index("--python-platform") + 1] == "linux"
    assert str(integration_input) in command


def test_build_compile_requirements_command_uses_platform_override(
    tmp_path: Path,
) -> None:
    """An explicit platform override should win over OS normalization."""
    command = build_compile_requirements_command(
        python_version="3.13",
        target_os="Linux",
        target_platform="x86_64-manylinux_2_35",
        output_path=tmp_path / "requirements.txt",
        input_paths=[],
    )

    assert command[command.index("--python-platform") + 1] == (
        "x86_64-manylinux_2_35"
    )


def test_write_compiled_requirements_invokes_uv_compile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Compiled export should resolve via uv after writing integration inputs."""

    def fake_write_integration_input_requirements(**kwargs):
        kwargs["output_path"].write_text("numpy<3.0\n", encoding="utf-8")
        return kwargs["output_path"]

    def fake_run(cmd, *, check, cwd):
        output_path = Path(cmd[cmd.index("--output-file") + 1])
        output_path.write_text("numpy==2.0.0\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(
        "scripts.install_dev_requirements.write_integration_input_requirements",
        fake_write_integration_input_requirements,
    )
    monkeypatch.setattr("scripts.install_dev_requirements.subprocess.run", fake_run)

    output_path = write_compiled_requirements(
        python_version="3.13",
        target_os="Linux",
        target_platform=None,
        output_path=tmp_path / "requirements.txt",
        include_integrations=True,
        root=tmp_path,
    )

    assert output_path.read_text(encoding="utf-8") == "numpy==2.0.0\n"
