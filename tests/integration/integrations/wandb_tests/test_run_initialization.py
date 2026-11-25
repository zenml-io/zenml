"""Tests for Wandb run initialization helpers."""

import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

wandb_module = ModuleType("wandb")
wandb_module.run = None
wandb_module.Settings = type("Settings", (), {})
wandb_module.init = lambda **_: None
wandb_module.finish = lambda **_: None

weave_module = ModuleType("weave")
weave_module.init = lambda **_: None

sys.modules.setdefault("wandb", wandb_module)
sys.modules.setdefault("weave", weave_module)


@pytest.fixture(scope="session", autouse=True)
def auto_environment():
    """Override the global ZenML test environment fixture."""
    return SimpleNamespace(), SimpleNamespace()


@pytest.fixture(scope="module", autouse=True)
def check_module_requirements():
    """Skip stack requirement checks for isolated Wandb integration tests."""
    return None


def _config() -> Any:
    from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
        WandbExperimentTrackerConfig,
    )

    return WandbExperimentTrackerConfig(
        api_key="key",
        entity="entity",
        project_name="project",
    )


def _settings(**kwargs: Any) -> Any:
    from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
        WandbExperimentTrackerSettings,
    )

    return WandbExperimentTrackerSettings(
        enable_zenml_dashboard_links=False,
        **kwargs,
    )


def _build_wandb_initialization(**kwargs: Any) -> Any:
    from zenml.integrations.wandb.experiment_trackers.run_initialization import (
        build_wandb_initialization,
    )

    return build_wandb_initialization(**kwargs)


def _info(
    *,
    run_id: UUID = UUID("00000000-0000-0000-0000-000000000001"),
    step_run_id: UUID = UUID("00000000-0000-0000-0000-000000000002"),
    pipeline_step_name: str = "train_model",
    version: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        step_run_id=step_run_id,
        run_id=run_id,
        run_name="training_pipeline-2026_05_14",
        pipeline_step_name=pipeline_step_name,
        pipeline=SimpleNamespace(name="training_pipeline"),
        step_run=SimpleNamespace(version=version),
    )


def test_default_initialization_adds_zenml_metadata_without_run_id() -> None:
    """Test default Wandb kwargs include ZenML metadata but no run ID."""
    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=_settings(),
        info=_info(),
    )

    assert init_kwargs["entity"] == "entity"
    assert init_kwargs["project"] == "project"
    assert init_kwargs["name"] == "training_pipeline-2026_05_14_train_model"
    assert "id" not in init_kwargs
    assert "resume" not in init_kwargs
    assert init_kwargs["settings"] == {
        "console": "off",
        "silent": True,
    }
    assert init_kwargs["group"] == "training_pipeline-2026_05_14"
    assert init_kwargs["tags"] == [
        "zenml",
        "training_pipeline",
        "training_pipeline-2026_05_14",
    ]
    assert init_kwargs["config"] == {
        "zenml_pipeline_name": "training_pipeline",
        "zenml_pipeline_run_id": "00000000-0000-0000-0000-000000000001",
        "zenml_pipeline_run_name": "training_pipeline-2026_05_14",
        "zenml_step_name": "train_model",
        "zenml_latest_step_run_id": "00000000-0000-0000-0000-000000000002",
        "zenml_latest_step_run_version": 1,
    }
    assert "job_type" not in init_kwargs


def test_wandb_console_output_can_be_enabled_with_settings() -> None:
    """Test W&B console settings can override ZenML's quiet defaults."""
    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            settings={
                "console": "auto",
                "show_info": True,
                "silent": False,
            },
        ),
        info=_info(),
    )

    assert init_kwargs["settings"] == {
        "console": "auto",
        "show_info": True,
        "silent": False,
    }


def test_user_tags_merge_with_human_readable_zenml_tags() -> None:
    """Test user tags are merged with readable ZenML tags."""
    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            tags=["team", "zenml"],
        ),
        info=_info(),
    )

    assert init_kwargs["tags"] == [
        "team",
        "zenml",
        "training_pipeline",
        "training_pipeline-2026_05_14",
    ]


def test_minimal_mode_omits_zenml_group_tags_and_config() -> None:
    """Test disabling ZenML metadata keeps Wandb initialization minimal."""
    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            enable_zenml_metadata=False,
            tags=["team"],
            run_config={"owner": "ml-platform"},
        ),
        info=_info(),
    )

    assert "group" not in init_kwargs
    assert init_kwargs["tags"] == ["team"]
    assert init_kwargs["config"] == {"owner": "ml-platform"}


def test_new_on_retry_strategy_sets_deterministic_run_id_and_resume() -> None:
    """Test retry attempts produce separate deterministic W&B run IDs."""
    first = _build_wandb_initialization(
        config=_config(),
        settings=_settings(run_id_strategy="new_on_retry"),
        info=_info(
            step_run_id=UUID("00000000-0000-0000-0000-000000000002"),
            version=1,
        ),
    )
    second = _build_wandb_initialization(
        config=_config(),
        settings=_settings(run_id_strategy="new_on_retry"),
        info=_info(
            step_run_id=UUID("00000000-0000-0000-0000-000000000003"),
            version=2,
        ),
    )

    assert first["id"] != second["id"]
    assert first["name"] == "training_pipeline-2026_05_14_train_model_v1"
    assert second["name"] == "training_pipeline-2026_05_14_train_model_v2"
    assert first["resume"] == "allow"
    assert second["resume"] == "allow"


def test_reuse_on_retry_strategy_collapses_retries() -> None:
    """Test retries resume one W&B run for the same step invocation."""
    first = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            run_id_strategy="reuse_on_retry",
        ),
        info=_info(
            step_run_id=UUID("00000000-0000-0000-0000-000000000002"),
            version=1,
        ),
    )
    retry = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            run_id_strategy="reuse_on_retry",
        ),
        info=_info(
            step_run_id=UUID("00000000-0000-0000-0000-000000000003"),
            version=2,
        ),
    )

    assert first["id"] == retry["id"]
    assert first["name"] == retry["name"]
    assert retry["config"]["zenml_latest_step_run_id"] == (
        "00000000-0000-0000-0000-000000000003"
    )
    assert retry["config"]["zenml_latest_step_run_version"] == 2


def test_reuse_on_retry_strategy_separates_invocation_names() -> None:
    """Test reused retry IDs still include concrete invocation names."""
    settings = _settings(
        run_id_strategy="reuse_on_retry",
    )

    first = _build_wandb_initialization(
        config=_config(),
        settings=settings,
        info=_info(pipeline_step_name="train_model"),
    )
    second = _build_wandb_initialization(
        config=_config(),
        settings=settings,
        info=_info(pipeline_step_name="train_model_2"),
    )

    assert first["id"] != second["id"]


def test_explicit_run_id_sets_resume_allow_by_default() -> None:
    """Test explicit Wandb run IDs default to resume allow."""
    settings = _settings(run_id="external-run-id")

    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=settings,
        info=_info(),
    )

    assert init_kwargs["id"] == "external-run-id"
    assert init_kwargs["resume"] == "allow"


def test_job_type_is_only_passed_when_configured() -> None:
    """Test job type is omitted unless explicitly configured."""
    without_job_type = _build_wandb_initialization(
        config=_config(),
        settings=_settings(),
        info=_info(),
    )
    with_job_type = _build_wandb_initialization(
        config=_config(),
        settings=_settings(job_type="training"),
        info=_info(),
    )

    assert "job_type" not in without_job_type
    assert with_job_type["job_type"] == "training"


def test_dashboard_links_are_added_when_available(monkeypatch) -> None:
    """Test available ZenML dashboard links are added to Wandb config."""
    monkeypatch.setattr(
        "zenml.integrations.wandb.experiment_trackers.run_initialization"
        "._get_dashboard_links",
        lambda info: {
            "zenml_pipeline_run_url": "https://zenml.example/runs/1"
        },
    )

    from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
        WandbExperimentTrackerSettings,
    )

    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=WandbExperimentTrackerSettings(),
        info=_info(),
    )

    assert init_kwargs["config"]["zenml_pipeline_run_url"] == (
        "https://zenml.example/runs/1"
    )


def test_step_metadata_includes_richer_wandb_identifiers(monkeypatch) -> None:
    """Test ZenML step metadata stores durable Wandb identifiers."""
    from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
    from zenml.integrations.wandb.experiment_trackers import (
        wandb_experiment_tracker as tracker_module,
    )

    wandb_run = SimpleNamespace(
        id="wandb-id",
        path="entity/project/wandb-id",
        name="display-name",
        group="group",
        project="project",
        entity="entity",
        job_type="training",
        url="https://wandb.ai/entity/project/runs/wandb-id",
    )
    monkeypatch.setattr(tracker_module.wandb, "run", wandb_run)

    tracker = object.__new__(tracker_module.WandbExperimentTracker)
    tracker._config = _config()
    monkeypatch.setattr(tracker, "get_settings", lambda info: _settings())

    metadata = tracker.get_step_run_metadata(_info())

    assert metadata[METADATA_EXPERIMENT_TRACKER_URL] == (
        "https://wandb.ai/entity/project/runs/wandb-id"
    )
    assert metadata["wandb_run_id"] == "wandb-id"
    assert metadata["wandb_run_path"] == "entity/project/wandb-id"
    assert metadata["wandb_run_name"] == "display-name"
    assert metadata["wandb_group"] == "group"
    assert metadata["wandb_project"] == "project"
    assert metadata["wandb_entity"] == "entity"
    assert metadata["wandb_job_type"] == "training"
    assert metadata["wandb_url"] == (
        "https://wandb.ai/entity/project/runs/wandb-id"
    )


@pytest.mark.parametrize(
    "settings_kwargs,error_match",
    [
        (
            {"run_id_strategy": "reuse_on_retry", "resume": "never"},
            "resume='never'",
        ),
        (
            {"run_id": "explicit", "run_id_strategy": "new_on_retry"},
            "run_id",
        ),
        (
            {"resume": "must"},
            "resume='must'",
        ),
        (
            {"run_config": {"zenml_pipeline_name": "override"}},
            "run_config",
        ),
        (
            {"init_kwargs": {"config": {"owner": "team"}}},
            "init_kwargs",
        ),
    ],
)
def test_invalid_settings_fail_early(
    settings_kwargs: dict, error_match: str
) -> None:
    """Test invalid Wandb settings combinations fail during validation."""
    with pytest.raises(ValueError, match=error_match):
        _settings(**settings_kwargs)


def test_unmanaged_init_kwargs_pass_through() -> None:
    """Test unmanaged Wandb init kwargs are passed through."""
    init_kwargs = _build_wandb_initialization(
        config=_config(),
        settings=_settings(
            init_kwargs={"mode": "offline"},
        ),
        info=_info(),
    )

    assert init_kwargs["mode"] == "offline"
