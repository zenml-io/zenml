"""Check explicit Modal placement before either submission allocates resources."""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize(
    "module_name", ["run_modal_training", "run_modal_baseline"]
)
@pytest.mark.parametrize(
    "mismatch", [None, "workspace", "environment", "credentials"]
)
@pytest.mark.parametrize("component_index", [0, 1])
def test_submission_checks_both_component_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    mismatch: str | None,
    component_index: int,
) -> None:
    """Submit custom placement only when both authenticated components agree.

    Args:
        tmp_path: Temporary bundle and configuration directory.
        monkeypatch: Scoped external boundary replacements.
        module_name: Training or baseline submission entry point.
        mismatch: Optional failing identity check.
        component_index: Orchestrator or sandbox identity to reject.
    """
    module = importlib.import_module(module_name)
    values = json.loads(
        (Path(__file__).parents[1] / "modal-training.example.json").read_text()
    )
    values["service"].update(
        workspace="external-team", modal_environment="research"
    )
    values["sandbox"].update(
        modal_workspace="external-team", modal_environment="research"
    )
    if module_name == "run_modal_baseline":
        task_id = values["training"]["task_ids"][0]
        values = {
            "controller_image": values["controller_image"],
            "task_ids": [task_id],
            "sandbox": values["sandbox"],
            "service": values["service"],
            "modal_agent_images": {
                task_id: values["sandbox"]["modal_agent_image"]
            },
        }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(values))
    (tmp_path / "task-manifest.json").write_text("{}")
    monkeypatch.setattr(
        sys,
        "argv",
        [module_name, "--bundle", str(tmp_path), "--config", str(config_path)],
    )
    monkeypatch.setattr(module, "load_bundle_task", Mock())
    orchestrator = Mock(spec=module.ModalOrchestrator)
    sandbox = Mock(spec=module.ModalSandbox)
    for component in (orchestrator, sandbox):
        component.config = SimpleNamespace(
            modal_environment="research",
            token_id="test-id",
            token_secret="test-secret",
        )
    rejected = (orchestrator, sandbox)[component_index]
    if mismatch == "environment":
        rejected.config.modal_environment = "other"
    elif mismatch == "credentials":
        rejected.config.token_id = None
    monkeypatch.setattr(
        module,
        "Client",
        Mock(
            return_value=SimpleNamespace(
                active_stack=SimpleNamespace(
                    orchestrator=orchestrator, sandbox=sandbox
                )
            )
        ),
    )
    monkeypatch.setattr(module, "create_modal_client_from_credentials", Mock())
    workspaces = ["external-team", "external-team"]
    if mismatch == "workspace":
        workspaces[component_index] = "wrong-team"
    sdk = Mock()
    sdk.Workspace.from_context.side_effect = [
        Mock(hydrate=Mock(return_value=SimpleNamespace(name=name)))
        for name in workspaces
    ]
    monkeypatch.setattr(module, "modal", sdk)
    publish = Mock(return_value=SimpleNamespace(id="artifact-id"))
    monkeypatch.setattr(module, "save_artifact", publish)
    pipeline = Mock()
    pipeline_name = (
        "endless_terminals_native_training"
        if module_name == "run_modal_training"
        else "endless_terminals_modal_baseline"
    )
    monkeypatch.setattr(module, pipeline_name, pipeline)
    if mismatch:
        with pytest.raises(RuntimeError):
            module.main()
        publish.assert_not_called()
        pipeline.with_options.assert_not_called()
    else:
        module.main()
        assert sdk.Workspace.from_context.call_count == 2
        settings = pipeline.with_options.call_args.kwargs["settings"]
        assert settings["orchestrator"].modal_environment == "research"
        pipeline.with_options.return_value.assert_called_once()
        publish.assert_called_once()
