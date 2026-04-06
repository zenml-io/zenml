"""Unit tests for Modal image cache helpers."""

from pathlib import Path

from scripts.ci.modal_image import (
    CachedExecutionImageManifest,
    CachedImageManifest,
    compute_execution_fingerprint,
    execution_overlay_paths_for_suite,
    load_cached_dependency_manifest,
    load_cached_execution_manifest,
    save_cached_execution_manifest,
    save_cached_manifest,
)


def _create_execution_fingerprint_root(root: Path) -> None:
    """Create the minimum file tree required for execution fingerprinting."""
    (root / "zen-test").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "install-zenml-dev.sh").write_text(
        "#!/usr/bin/env bash\n",
        encoding="utf-8",
    )
    (root / "scripts" / "helper.py").write_text("print('helper')\n", encoding="utf-8")
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


def test_compute_execution_fingerprint_changes_when_source_changes(
    tmp_path: Path,
) -> None:
    """Changing synced source files should invalidate the execution cache."""
    _create_execution_fingerprint_root(tmp_path)

    fingerprint_before = compute_execution_fingerprint(
        python_version="3.13",
        test_environment="default",
        dependency_fingerprint="dependency-fingerprint",
        suite_name="unit",
        root=tmp_path,
    )

    (tmp_path / "src" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")

    fingerprint_after = compute_execution_fingerprint(
        python_version="3.13",
        test_environment="default",
        dependency_fingerprint="dependency-fingerprint",
        suite_name="unit",
        root=tmp_path,
    )

    assert fingerprint_before != fingerprint_after


def test_compute_execution_fingerprint_ignores_irrelevant_suite_changes(
    tmp_path: Path,
) -> None:
    """Integration fingerprints should ignore unit-only test edits."""
    _create_execution_fingerprint_root(tmp_path)
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "example.py").write_text(
        "print('example')\n",
        encoding="utf-8",
    )

    fingerprint_before = compute_execution_fingerprint(
        python_version="3.13",
        test_environment="default",
        dependency_fingerprint="dependency-fingerprint",
        suite_name="integration",
        root=tmp_path,
    )

    (tmp_path / "tests" / "unit" / "test_module.py").write_text(
        "def test_changed():\n    assert True\n",
        encoding="utf-8",
    )

    fingerprint_after = compute_execution_fingerprint(
        python_version="3.13",
        test_environment="default",
        dependency_fingerprint="dependency-fingerprint",
        suite_name="integration",
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


def test_save_cached_manifests_preserve_multiple_entries(tmp_path: Path) -> None:
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
    save_cached_execution_manifest(
        CachedExecutionImageManifest(
            fingerprint="exec-1",
            image_id="im-exec-1",
            python_version="3.13",
            test_environment="default",
            dependency_fingerprint="dep-1",
            suite_name="unit",
        ),
        manifest_path=manifest_path,
    )

    dependency_manifest = load_cached_dependency_manifest(
        fingerprint="dep-2",
        manifest_path=manifest_path,
    )
    execution_manifest = load_cached_execution_manifest(
        fingerprint="exec-1",
        manifest_path=manifest_path,
    )

    assert dependency_manifest == CachedImageManifest(
        fingerprint="dep-2",
        image_id="im-dep-2",
        python_version="3.13",
    )
    assert execution_manifest == CachedExecutionImageManifest(
        fingerprint="exec-1",
        image_id="im-exec-1",
        python_version="3.13",
        test_environment="default",
        dependency_fingerprint="dep-1",
        suite_name="unit",
    )


def test_execution_overlay_paths_include_shared_and_suite_specific_paths() -> None:
    """Suite overlays should include shared support files plus suite content."""
    assert execution_overlay_paths_for_suite("unit") == (
        "zen-test",
        "scripts",
        "src",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/venv_clone_utils.py",
        "tests/harness",
        "tests/unit",
    )
    assert execution_overlay_paths_for_suite("integration") == (
        "zen-test",
        "scripts",
        "src",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/venv_clone_utils.py",
        "tests/harness",
        "tests/integration",
        "examples",
    )
