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

# ruff: noqa: D100,D101,D102,D103,D105,D107

import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.baseten.flavors import (
    BasetenStepOperatorConfig,
    BasetenStepOperatorSettings,
)
from zenml.integrations.baseten.step_operators import BasetenStepOperator
from zenml.integrations.baseten.step_operators import (
    baseten_step_operator as op_module,
)

SENSITIVE_KEY = "ZENML_STORE_API_TOKEN"


class _Node:
    """Records the kwargs it is constructed with (fake truss definition)."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__dict__.update(kwargs)


@pytest.fixture
def fake_truss(monkeypatch):
    """Replace the truss objects bound in the operator module with fakes.

    truss is imported at module top, so the names live on the operator module;
    patch them there rather than via sys.modules.
    """
    recorded = {}

    def push(config, source_dir=None, remote=None):
        recorded["config"] = config
        recorded["source_dir"] = source_dir
        recorded["remote"] = remote
        return {"id": "job-123", "training_project_id": "proj-456"}

    definitions = types.SimpleNamespace(
        TrainingProject=_Node,
        TrainingJob=_Node,
        Image=_Node,
        Compute=_Node,
        Runtime=_Node,
        SecretReference=_Node,
        DockerAuth=_Node,
        RegistrySecretDockerAuth=_Node,
        CacheConfig=_Node,
        CheckpointingConfig=_Node,
    )
    truss_config = types.SimpleNamespace(
        AcceleratorSpec=_Node,
        DockerAuthType=types.SimpleNamespace(
            REGISTRY_SECRET="registry_secret"
        ),
    )

    class _RemoteFactory:
        @staticmethod
        def update_remote_config(config):
            recorded["remote_config"] = config

    # Default active stack: a container registry with no credentials (public),
    # so _docker_auth resolves to None unless a test overrides it.
    registry = SimpleNamespace(
        config=SimpleNamespace(uri="registry.example.com"), credentials=None
    )
    stack = SimpleNamespace(container_registry=registry)
    recorded["registry"] = registry

    monkeypatch.setattr(op_module, "push", push)
    monkeypatch.setattr(op_module, "definitions", definitions)
    monkeypatch.setattr(op_module, "truss_config", truss_config)
    monkeypatch.setattr(op_module, "RemoteFactory", _RemoteFactory)
    monkeypatch.setattr(op_module, "RemoteConfig", _Node)
    monkeypatch.setattr(
        op_module, "Client", lambda: SimpleNamespace(active_stack=stack)
    )
    return recorded


def _make_operator(**config_kwargs) -> BasetenStepOperator:
    config = BasetenStepOperatorConfig(
        api_key="bt-secret", project="zenml-training", **config_kwargs
    )
    operator = BasetenStepOperator(
        name="baseten",
        id=uuid4(),
        config=config,
        flavor="baseten",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    operator.id = "component-id"
    return operator


def _make_info(
    command=None, gpu_count=1, cpu_count=None, memory=None, run_metadata=None
):
    resource_settings = SimpleNamespace(
        gpu_count=gpu_count, cpu_count=cpu_count, memory=memory
    )
    config = SimpleNamespace(
        command=command, resource_settings=resource_settings
    )
    step_run = SimpleNamespace(
        run_metadata=run_metadata if run_metadata is not None else {}
    )
    return SimpleNamespace(
        step_run_id="step-run-id",
        pipeline_step_name="train",
        config=config,
        step_run=step_run,
        get_image=lambda key: "registry.example.com/zenml:latest",
    )


def _entrypoint():
    return ["torchrun", "train.py"]


# --- the multi-node gate -----------------------------------------------------


def test_gate_rejects_multi_node_regular_step(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings(
        node_count=4
    )
    info = _make_info(command=None)

    with pytest.raises(RuntimeError, match="node_count=4"):
        operator.submit(info, _entrypoint(), {})


def test_gate_allows_multi_node_command_step(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings(
        node_count=4, accelerator="H200"
    )
    info = _make_info(command=["torchrun", "train.py"], gpu_count=8)

    operator.submit(info, _entrypoint(), {})

    job = fake_truss["config"].job
    assert job.compute.node_count == 4
    assert job.compute.accelerator.accelerator == "H200"
    assert job.compute.accelerator.count == 8


def test_single_node_regular_step_submits(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    info = _make_info(command=None)

    operator.submit(info, _entrypoint(), {})

    assert fake_truss["config"].job.compute.node_count == 1


# --- source_dir / workdir handling ------------------------------------------


def test_submit_uses_empty_source_dir_and_disables_workdir(
    fake_truss, monkeypatch
):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()

    operator.submit(_make_info(), _entrypoint(), {})

    source_dir = fake_truss["source_dir"]
    assert isinstance(source_dir, Path)
    # The temp dir is cleaned up after push, so it should be empty/gone.
    assert not list(source_dir.glob("*")) if source_dir.exists() else True
    assert fake_truss["config"].job.enable_baseten_workdir is False


# --- cache / checkpointing (opt-in) ------------------------------------------


def test_cache_and_checkpointing_disabled_by_default(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    operator.submit(_make_info(), _entrypoint(), {})
    runtime = fake_truss["config"].job.runtime
    assert "cache_config" not in runtime.kwargs
    assert "checkpointing_config" not in runtime.kwargs


def test_cache_and_checkpointing_enabled(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings(
        enable_cache=True, enable_checkpointing=True
    )
    operator.submit(_make_info(), _entrypoint(), {})
    runtime = fake_truss["config"].job.runtime
    assert runtime.cache_config.enabled is True
    # Defaults mirror truss: no legacy HF mount, affinity required.
    assert runtime.cache_config.enable_legacy_hf_mount is False
    assert runtime.cache_config.require_cache_affinity is True
    assert runtime.checkpointing_config.enabled is True


def test_cache_legacy_hf_mount_and_affinity_overrides(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings(
        enable_cache=True,
        cache_enable_legacy_hf_mount=True,
        cache_require_affinity=False,
    )
    operator.submit(_make_info(), _entrypoint(), {})
    cache_config = fake_truss["config"].job.runtime.cache_config
    assert cache_config.enable_legacy_hf_mount is True
    assert cache_config.require_cache_affinity is False


# --- environment / secrets ---------------------------------------------------


def test_build_environment_maps_secret_reference(fake_truss):
    operator = _make_operator()
    result = operator._build_environment(
        {"HF_TOKEN": "value"}, {"HF_TOKEN": "hf-secret"}
    )
    assert isinstance(result["HF_TOKEN"], _Node)
    assert result["HF_TOKEN"].name == "hf-secret"


def test_build_environment_inlines_plain_values(fake_truss):
    operator = _make_operator()
    result = operator._build_environment({"EPOCHS": "5"}, {})
    assert result == {"EPOCHS": "5"}


def test_build_environment_passes_store_token_through(fake_truss):
    # The store token is treated like any other env var (no special-casing):
    # passed through unless the user explicitly maps it to a Baseten secret.
    operator = _make_operator()
    result = operator._build_environment({SENSITIVE_KEY: "tok"}, {})
    assert result == {SENSITIVE_KEY: "tok"}


def test_build_environment_allows_mapped_store_token(fake_truss):
    operator = _make_operator()
    result = operator._build_environment(
        {SENSITIVE_KEY: "tok"}, {SENSITIVE_KEY: "zenml-token-secret"}
    )
    assert isinstance(result[SENSITIVE_KEY], _Node)
    assert result[SENSITIVE_KEY].name == "zenml-token-secret"


# --- docker auth -------------------------------------------------------------


def test_docker_auth_built_from_explicit_registry_secret(
    fake_truss, monkeypatch
):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )

    operator = _make_operator(registry_auth_secret="gcr-creds")
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    operator.submit(_make_info(), _entrypoint(), {})

    docker_auth = fake_truss["config"].job.image.docker_auth
    assert docker_auth is not None
    assert (
        docker_auth.registry_secret_docker_auth.secret_ref.name == "gcr-creds"
    )


def test_docker_auth_none_for_public_registry(fake_truss, monkeypatch):
    # Fixture default: container registry has no credentials -> no auth.
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    operator.submit(_make_info(), _entrypoint(), {})
    assert fake_truss["config"].job.image.docker_auth is None


def test_docker_auth_auto_created_from_registry_credentials(
    fake_truss, monkeypatch
):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )
    fake_truss["registry"].credentials = ("user", "pass")

    upserted = {}
    operator = _make_operator()
    operator._api = SimpleNamespace(
        upsert_secret=lambda name, value: upserted.update({name: value})
    )
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    operator.submit(_make_info(), _entrypoint(), {})

    secret_name = "zenml-registry-auth-component-id"
    assert upserted == {secret_name: "user:pass"}
    docker_auth = fake_truss["config"].job.image.docker_auth
    assert (
        docker_auth.registry_secret_docker_auth.secret_ref.name == secret_name
    )


# --- metadata recording ------------------------------------------------------


def test_submit_records_both_ids_as_metadata(fake_truss, monkeypatch):
    published = {}

    def _publish(step_run_id, metadata):
        published["args"] = (step_run_id, metadata)

    monkeypatch.setattr(op_module, "publish_step_run_metadata", _publish)
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()
    info = _make_info()

    operator.submit(info, _entrypoint(), {})

    step_run_id, metadata = published["args"]
    assert step_run_id == "step-run-id"
    payload = metadata["component-id"]
    assert payload[op_module.BASETEN_JOB_ID_METADATA_KEY] == "job-123"
    assert payload[op_module.BASETEN_PROJECT_ID_METADATA_KEY] == "proj-456"
    assert (
        payload[op_module.BASETEN_LOGS_URL_METADATA_KEY]
        == "https://app.baseten.co/training/project/proj-456/logs/job-123"
    )
    assert (
        info.step_run.run_metadata[op_module.BASETEN_JOB_ID_METADATA_KEY]
        == "job-123"
    )


def test_submit_continues_when_metadata_publish_fails(fake_truss, monkeypatch):
    # The job is already running on Baseten, so a metadata-persist failure is
    # logged but must not fail the step.
    def _boom(*args, **kwargs):
        raise RuntimeError("publish failed")

    monkeypatch.setattr(op_module, "publish_step_run_metadata", _boom)
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()

    operator.submit(_make_info(), _entrypoint(), {})  # does not raise


# --- submit error translation ------------------------------------------------


class _HttpError(Exception):
    """Stand-in for a requests.HTTPError carrying a response body."""

    def __init__(self, message, body):
        super().__init__(message)
        self.response = SimpleNamespace(text=body)


def test_explain_submit_error_flags_custom_base_image():
    err = _HttpError(
        "400 Client Error: Bad Request",
        "Custom base images not supported for your organization.",
    )
    msg = op_module._explain_submit_error(
        err, BasetenStepOperatorSettings(), is_command_step=False
    )
    assert "custom base images" in msg.lower()
    assert "Baseten" in msg
    # Original detail and response body are preserved.
    assert "400 Client Error" in msg


def test_explain_submit_error_flags_multi_node():
    err = _HttpError("400 Client Error: Bad Request", "")
    msg = op_module._explain_submit_error(
        err,
        BasetenStepOperatorSettings(node_count=4),
        is_command_step=True,
    )
    assert "multi-node instance types" in msg.lower()
    assert "node_count=4" in msg


def test_submit_wraps_push_errors(fake_truss, monkeypatch):
    monkeypatch.setattr(
        op_module, "publish_step_run_metadata", lambda *a: None
    )

    def _boom(*args, **kwargs):
        raise _HttpError(
            "400 Client Error", "Custom base images not supported"
        )

    monkeypatch.setattr(op_module, "push", _boom)
    operator = _make_operator()
    operator.get_settings = lambda _info: BasetenStepOperatorSettings()

    with pytest.raises(RuntimeError, match="custom base images"):
        operator.submit(_make_info(), _entrypoint(), {})


# --- status mapping ----------------------------------------------------------


class _FakeApi:
    def __init__(self, state):
        self._state = state
        self.stopped = None

    def get_job_status(self, project_id, job_id):
        self._last = (project_id, job_id)
        return self._state

    def stop_job(self, project_id, job_id):
        self.stopped = (project_id, job_id)


def _step_run_with_ids():
    return SimpleNamespace(
        run_metadata={
            op_module.BASETEN_JOB_ID_METADATA_KEY: "job-123",
            op_module.BASETEN_PROJECT_ID_METADATA_KEY: "proj-456",
        }
    )


@pytest.mark.parametrize(
    "state, expected",
    [
        ("TRAINING_JOB_PENDING", ExecutionStatus.QUEUED),
        ("TRAINING_JOB_CREATED", ExecutionStatus.INITIALIZING),
        ("TRAINING_JOB_DEPLOYING", ExecutionStatus.PROVISIONING),
        ("TRAINING_JOB_RUNNING", ExecutionStatus.RUNNING),
        ("TRAINING_JOB_COMPLETED", ExecutionStatus.COMPLETED),
        ("TRAINING_JOB_FAILED", ExecutionStatus.FAILED),
        ("DEPLOY_FAILED", ExecutionStatus.FAILED),
        ("TRAINING_JOB_STOPPED", ExecutionStatus.STOPPED),
        ("COMPLETED", ExecutionStatus.COMPLETED),
        ("STOPPED", ExecutionStatus.STOPPED),
        ("SOMETHING_NEW", ExecutionStatus.RUNNING),
    ],
)
def test_get_status_maps_states(state, expected):
    operator = _make_operator()
    operator._api = _FakeApi(state)
    assert operator.get_status(_step_run_with_ids()) == expected


def test_get_status_missing_ids_returns_failed():
    operator = _make_operator()
    operator._api = _FakeApi("RUNNING")
    step_run = SimpleNamespace(run_metadata={})
    assert operator.get_status(step_run) == ExecutionStatus.FAILED


def test_get_status_missing_job_returns_failed():
    operator = _make_operator()
    operator._api = _FakeApi(None)  # 404 -> None
    assert operator.get_status(_step_run_with_ids()) == ExecutionStatus.FAILED


# --- cancel ------------------------------------------------------------------


def test_cancel_stops_job_with_both_ids():
    operator = _make_operator()
    api = _FakeApi("RUNNING")
    operator._api = api
    operator.cancel(_step_run_with_ids())
    assert api.stopped == ("proj-456", "job-123")


def test_cancel_noop_without_ids():
    operator = _make_operator()
    api = _FakeApi("RUNNING")
    operator._api = api
    operator.cancel(SimpleNamespace(run_metadata={}))
    assert api.stopped is None


# --- validator ---------------------------------------------------------------


def test_validator_rejects_local_artifact_store():
    operator = _make_operator()
    stack = SimpleNamespace(
        artifact_store=SimpleNamespace(
            name="local", config=SimpleNamespace(is_local=True)
        )
    )
    ok, msg = operator.validator._custom_validation_function(stack)
    assert ok is False
    assert "remote artifact store" in msg


def test_validator_rejects_local_container_registry():
    operator = _make_operator()
    stack = SimpleNamespace(
        artifact_store=SimpleNamespace(
            name="s3", config=SimpleNamespace(is_local=False)
        ),
        container_registry=SimpleNamespace(
            name="local", config=SimpleNamespace(is_local=True)
        ),
    )
    ok, msg = operator.validator._custom_validation_function(stack)
    assert ok is False
    assert "remote container registry" in msg


def test_validator_requires_registry_and_image_builder():
    operator = _make_operator()
    required = operator.validator._required_components
    assert StackComponentType.CONTAINER_REGISTRY in required
    assert StackComponentType.IMAGE_BUILDER in required


def test_validator_accepts_remote_components():
    operator = _make_operator()
    stack = SimpleNamespace(
        artifact_store=SimpleNamespace(
            name="s3", config=SimpleNamespace(is_local=False)
        ),
        container_registry=SimpleNamespace(
            name="gcr", config=SimpleNamespace(is_local=False)
        ),
    )
    ok, msg = operator.validator._custom_validation_function(stack)
    assert ok is True
    assert msg == ""


# --- REST API client ---------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _client():
    from zenml.integrations.baseten.baseten_api import BasetenApiClient

    return BasetenApiClient("bt-key")


def test_api_get_status_reads_nested_training_job(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests.Session,
        "get",
        lambda self, *a, **k: _FakeResponse(
            200, {"training_job": {"current_status": "TRAINING_JOB_COMPLETED"}}
        ),
    )
    assert _client().get_job_status("p", "j") == "TRAINING_JOB_COMPLETED"


def test_api_get_status_missing_training_job_returns_none(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests.Session,
        "get",
        lambda self, *a, **k: _FakeResponse(200, {}),
    )
    assert _client().get_job_status("p", "j") is None


def test_api_get_status_returns_none_on_404(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests.Session, "get", lambda self, *a, **k: _FakeResponse(404)
    )
    assert _client().get_job_status("p", "j") is None


def test_api_stop_job_posts_to_stop_endpoint(monkeypatch):
    import requests

    recorded = {}

    def _post(self, url, **kwargs):
        recorded["url"] = url
        recorded["json"] = kwargs.get("json")
        return _FakeResponse(200)

    monkeypatch.setattr(requests.Session, "post", _post)
    _client().stop_job("proj-1", "job-1")
    assert recorded["url"].endswith(
        "/training_projects/proj-1/jobs/job-1/stop"
    )
    assert recorded["json"] == {}


def test_api_client_sends_api_key_auth_header(monkeypatch):
    import requests

    captured = {}

    def _get(self, url, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _FakeResponse(
            200, {"training_job": {"current_status": "RUNNING"}}
        )

    monkeypatch.setattr(requests.Session, "get", _get)
    _client().get_job_status("p", "j")
    assert captured["headers"]["Authorization"] == "Api-Key bt-key"


def test_api_upsert_secret_posts_name_and_value(monkeypatch):
    import requests

    recorded = {}

    def _post(self, url, **kwargs):
        recorded["url"] = url
        recorded["json"] = kwargs.get("json")
        return _FakeResponse(200)

    monkeypatch.setattr(requests.Session, "post", _post)
    _client().upsert_secret("my-secret", "user:pass")
    assert recorded["url"].endswith("/v1/secrets")
    assert recorded["json"] == {"name": "my-secret", "value": "user:pass"}
