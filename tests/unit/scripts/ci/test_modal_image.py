"""Unit tests for Modal image cache helpers."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts.ci.modal_image import (
    CachedImageManifest,
    compute_collection_fingerprint,
    compute_dependency_fingerprint,
    export_dependency_requirements,
    load_cached_dependency_manifest,
    resolve_dependency_image,
    save_cached_manifest,
)


def _create_collection_fingerprint_root(root: Path) -> None:
    """Create the minimum file tree required for collection fingerprinting."""
    (root / "pyproject.toml").write_text(
        "[project]\nname='zenml'\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# ZenML\n", encoding="utf-8")
    (root / "zen-test").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "install-zenml-dev.sh").write_text(
        "#!/usr/bin/env bash\n",
        encoding="utf-8",
    )
    (root / "scripts" / "helper.py").write_text(
        "print('helper')\n", encoding="utf-8"
    )
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "conftest.py").write_text("", encoding="utf-8")
    (root / "tests" / "venv_clone_utils.py").write_text("", encoding="utf-8")
    (root / "tests" / "harness").mkdir()
    (root / "tests" / "harness" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (root / "tests" / "unit").mkdir()
    (root / "tests" / "unit" / "test_module.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "tests" / "integration").mkdir()
    (root / "tests" / "integration" / "test_module.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )


def test_compute_dependency_fingerprint_changes_when_requirements_change(
    tmp_path: Path,
) -> None:
    """Dependency fingerprints should track the generated requirements input."""
    requirements_path = tmp_path / "integration-requirements.txt"
    requirements_path.write_text("numpy<3.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='zenml'\n", encoding="utf-8"
    )

    fingerprint_before = compute_dependency_fingerprint(
        python_version="3.13",
        requirements_path=requirements_path,
    )

    requirements_path.write_text("numpy<3.0\nscipy\n", encoding="utf-8")

    fingerprint_after = compute_dependency_fingerprint(
        python_version="3.13",
        requirements_path=requirements_path,
    )

    assert fingerprint_before != fingerprint_after


def test_export_dependency_requirements_uses_install_script(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Dependency export should delegate to the dev install script."""
    commands: list[tuple[list[str], Path]] = []
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "zenml").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "zenml" / "integrations").mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='zenml'\n", encoding="utf-8"
    )
    (tmp_path / "scripts" / "install-zenml-dev.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    (tmp_path / "scripts" / "install_dev_requirements.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    (tmp_path / "src" / "zenml" / "integrations" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    def fake_run(cmd, *, check, cwd, capture_output, text):
        commands.append((cmd, Path(cwd)))
        output_path = Path(cmd[cmd.index("--export-requirements-file") + 1])
        output_path.write_text("numpy==2.0.0\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr("scripts.ci.modal_image.subprocess.run", fake_run)

    output_path = export_dependency_requirements(
        python_version="3.13",
        target_os="Linux",
        output_path=tmp_path / "requirements.txt",
        root=tmp_path,
    )

    assert output_path.read_text(encoding="utf-8") == "numpy==2.0.0\n"
    assert commands == [
        (
            [
                "/bin/sh",
                str(tmp_path / "scripts" / "install-zenml-dev.sh"),
                "--integrations",
                "yes",
                "--export-requirements-file",
                str(tmp_path / "requirements.txt"),
                "--target-python-version",
                "3.13",
                "--target-os",
                "Linux",
                "--target-platform",
                "x86_64-manylinux_2_35",
            ],
            tmp_path,
        )
    ]


def test_export_dependency_requirements_reuses_cached_export(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """A matching fingerprint should skip re-exporting requirements."""
    root = tmp_path
    (root / "scripts").mkdir()
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "zenml").mkdir(parents=True, exist_ok=True)
    (root / "src" / "zenml" / "integrations").mkdir(
        parents=True, exist_ok=True
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='zenml'\n", encoding="utf-8"
    )
    (root / "scripts" / "install-zenml-dev.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    (root / "scripts" / "install_dev_requirements.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    (root / "src" / "zenml" / "integrations" / "__init__.py").write_text(
        "", encoding="utf-8"
    )

    output_path = tmp_path / "requirements.txt"
    output_path.write_text("numpy==2.0.0\n", encoding="utf-8")
    fingerprint_path = output_path.with_suffix(".txt.fingerprint")
    from scripts.ci.modal_image import compute_requirements_export_fingerprint

    fingerprint_path.write_text(
        compute_requirements_export_fingerprint(
            python_version="3.13",
            target_os="Linux",
            target_platform="x86_64-manylinux_2_35",
            root=root,
        ),
        encoding="utf-8",
    )

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr("scripts.ci.modal_image.subprocess.run", fail_run)

    result = export_dependency_requirements(
        python_version="3.13",
        target_os="Linux",
        target_platform="x86_64-manylinux_2_35",
        output_path=output_path,
        root=root,
    )

    assert result == output_path


def test_resolve_dependency_image_uses_cached_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """A cached dependency image ID should skip rebuilding the definition."""
    manifest_path = tmp_path / "image-manifest.json"
    save_cached_manifest(
        CachedImageManifest(
            fingerprint="dep-fingerprint",
            image_id="im-dep-1",
            python_version="3.13",
        ),
        manifest_path=manifest_path,
    )

    monkeypatch.setattr(
        "scripts.ci.modal_image.export_dependency_requirements",
        lambda **kwargs: tmp_path / "requirements.txt",
    )
    monkeypatch.setattr(
        "scripts.ci.modal_image.compute_dependency_fingerprint",
        lambda **kwargs: "dep-fingerprint",
    )
    monkeypatch.setattr(
        "scripts.ci.modal_image._build_dependency_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("_build_dependency_image should not be called")
        ),
    )

    fake_modal = SimpleNamespace(
        Image=SimpleNamespace(from_id=lambda image_id: {"image_id": image_id})
    )
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    resolution = resolve_dependency_image(
        python_version="3.13",
        manifest_path=manifest_path,
    )

    assert resolution.image == {"image_id": "im-dep-1"}
    assert resolution.fingerprint == "dep-fingerprint"
    assert resolution.cache_hit is True


def test_compute_collection_fingerprint_ignores_src_only_changes(
    tmp_path: Path,
) -> None:
    """Node collection cache should survive application-only source edits."""
    _create_collection_fingerprint_root(tmp_path)

    fingerprint_before = compute_collection_fingerprint(
        python_version="3.13",
        test_environment="default",
        suite_name="integration",
        pytest_import_mode="importlib",
        root=tmp_path,
    )

    (tmp_path / "src" / "module.py").write_text(
        "VALUE = 99\n", encoding="utf-8"
    )

    fingerprint_after = compute_collection_fingerprint(
        python_version="3.13",
        test_environment="default",
        suite_name="integration",
        pytest_import_mode="importlib",
        root=tmp_path,
    )

    assert fingerprint_before == fingerprint_after


def test_load_cached_dependency_manifest_supports_legacy_layout(
    tmp_path: Path,
) -> None:
    """The new loader should still understand the old flat manifest."""
    manifest_path = tmp_path / "image-manifest.json"
    manifest_path.write_text(
        (
            "{\n"
            '  "fingerprint": "dep-1",\n'
            '  "image_id": "im-dep-1",\n'
            '  "python_version": "3.13"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    manifest = load_cached_dependency_manifest(
        fingerprint="dep-1",
        manifest_path=manifest_path,
    )

    assert manifest == CachedImageManifest(
        fingerprint="dep-1",
        image_id="im-dep-1",
        python_version="3.13",
    )


def test_save_cached_manifests_preserve_multiple_entries(
    tmp_path: Path,
) -> None:
    """Saving one cache entry should not overwrite unrelated cached images."""
    manifest_path = tmp_path / "image-manifest.json"

    save_cached_manifest(
        CachedImageManifest(
            fingerprint="dep-1",
            image_id="im-dep-1",
            python_version="3.13",
        ),
        manifest_path=manifest_path,
    )
    save_cached_manifest(
        CachedImageManifest(
            fingerprint="dep-2",
            image_id="im-dep-2",
            python_version="3.13",
        ),
        manifest_path=manifest_path,
    )
    dependency_manifest = load_cached_dependency_manifest(
        fingerprint="dep-2",
        manifest_path=manifest_path,
    )

    assert dependency_manifest == CachedImageManifest(
        fingerprint="dep-2",
        image_id="im-dep-2",
        python_version="3.13",
    )
