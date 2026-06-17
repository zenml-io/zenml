#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

# ruff: noqa: D100,D102,D103,D107

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

# Skip this entire module if the optional dependency isn't available, because
# the module under test imports `modal` at import time.
pytest.importorskip("modal")

from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.modal import sandbox_utils
from zenml.integrations.modal.flavors import (
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.integrations.modal.sandbox_utils import get_gpu_values
from zenml.integrations.modal.step_operators import (
    modal_step_operator as modal_step_operator_module,
)
from zenml.integrations.modal.step_operators.modal_step_operator import (
    ModalStepOperator,
)

SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY = (
    sandbox_utils.SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY
)


class ResourceSettingsStub:
    """Minimal stub to simulate ZenML ResourceSettings for GPU tests.

    We only model the attributes the helper and submit path use in the small
    targeted Modal tests. This keeps tests lightweight and avoids wider
    dependencies.
    """

    def __init__(self, gpu_count, cpu_count=None, memory_mb=None):
        self.gpu_count = gpu_count
        self.cpu_count = cpu_count
        self.memory_mb = memory_mb

    def get_memory(self, _unit):
        return self.memory_mb


class ModalClientStub:
    """Small stand-in for an opened Modal client."""

    def __init__(self, name: str):
        self.name = name
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed


def _make_operator(config: ModalStepOperatorConfig) -> ModalStepOperator:
    return ModalStepOperator(
        name="modal",
        id=uuid4(),
        config=config,
        flavor="modal",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _submit_with_stubs(
    monkeypatch,
    config: ModalStepOperatorConfig,
    settings: ModalStepOperatorSettings,
    modal_client: ModalClientStub | None,
    registry_credentials: tuple[str, str] | None = None,
    environment: dict[str, str] | None = None,
    publish_step_run_metadata_error: Exception | None = None,
    run_metadata=None,
    expect_submit_error: bool = False,
):
    recorded = {"client_credentials": [], "secret_values": []}
    resource_settings = ResourceSettingsStub(
        gpu_count=0,
        cpu_count=2,
        memory_mb=1.2,
    )
    if run_metadata is None:
        run_metadata = {}

    class InfoStub:
        step_run_id = "step-run-id"
        pipeline_step_name = "train"
        config = SimpleNamespace(resource_settings=resource_settings)
        step_run = SimpleNamespace(run_metadata=run_metadata)

        def get_image(self, key):
            assert key == "modal_step_operator"
            return "registry.example.com/zenml:latest"

    class ContainerRegistryStub:
        credentials = registry_credentials

    class StackStub:
        container_registry = ContainerRegistryStub()

    class ClientStub:
        active_stack = StackStub()

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded["client_credentials"].append((token_id, token_secret))
            assert modal_client is not None
            return modal_client

    class ImageStub:
        def env(self, environment):
            raise AssertionError(
                "ZenML runtime env must be passed to "
                "Sandbox.create(env=...), not Image.env(...)."
            )

    class ImageFactoryStub:
        @staticmethod
        def from_registry(image_name, **kwargs):
            recorded["image_name"] = image_name
            recorded["image_kwargs"] = kwargs
            image = ImageStub()
            recorded["image"] = image
            return image

    class SecretFactoryStub:
        @staticmethod
        def from_dict(values):
            secret = SimpleNamespace(values=dict(values))
            recorded["secret_values"].append(dict(values))
            recorded.setdefault("secrets", []).append(secret)
            return secret

    class AppFactoryStub:
        @staticmethod
        def lookup(*args, **kwargs):
            recorded["app_lookup"] = (args, kwargs)
            return "app"

    class SandboxStub:
        object_id = "sandbox-id"

        def __init__(self):
            self.terminate_calls = 0

        def terminate(self):
            self.terminate_calls += 1

    class SandboxFactoryStub:
        @staticmethod
        def create(*args, **kwargs):
            recorded["sandbox_create"] = (args, kwargs)
            sandbox = SandboxStub()
            recorded["sandbox"] = sandbox
            return sandbox

    operator = _make_operator(config)
    operator.id = "component-id"
    operator.get_settings = lambda _info: settings

    monkeypatch.setattr(modal_step_operator_module, "Client", ClientStub)
    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Image", ImageFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Secret", SecretFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "App", AppFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Sandbox", SandboxFactoryStub
    )

    def publish_step_run_metadata_stub(*args, **kwargs):
        if publish_step_run_metadata_error:
            raise publish_step_run_metadata_error
        recorded.setdefault("published_metadata", (args, kwargs))

    monkeypatch.setattr(
        modal_step_operator_module,
        "publish_step_run_metadata",
        publish_step_run_metadata_stub,
    )

    entrypoint_command = [
        "python",
        "-m",
        "zenml.entrypoints.entrypoint",
        "--step_name",
        "train model",
    ]
    if environment is None:
        environment = {
            "ZENML_ENV": "value",
            SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "sensitive-token",
        }

    if expect_submit_error:
        with pytest.raises(Exception) as e:
            operator.submit(InfoStub(), entrypoint_command, environment)
        recorded["submit_error"] = e.value
    else:
        operator.submit(InfoStub(), entrypoint_command, environment)

    return recorded, run_metadata, entrypoint_command, environment


def test_gpu_arg_none_when_no_type_and_no_count() -> None:
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs) is None


def test_gpu_arg_raises_when_count_without_type() -> None:
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=1)
    with pytest.raises(StackComponentInterfaceError) as e:
        get_gpu_values(settings, rs)
    error_message = str(e.value)
    assert (
        "GPU resources requested (gpu_count > 0) but no GPU type was specified"
        in error_message
    )
    assert "ModalStepOperatorSettings.gpu" in error_message
    assert "step_operator" in error_message
    assert "settings={'modal'" not in error_message


def test_gpu_arg_uses_custom_validation_message() -> None:
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=1)

    with pytest.raises(StackComponentInterfaceError) as e:
        get_gpu_values(
            settings,
            rs,
            gpu_settings_field="CustomSettings.gpu",
            gpu_settings_example="Set CustomSettings(gpu='A100').",
        )

    error_message = str(e.value)
    assert "CustomSettings.gpu" in error_message
    assert "Set CustomSettings(gpu='A100')." in error_message


def test_gpu_arg_type_with_no_count_returns_type() -> None:
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs) == "A100"


def test_gpu_arg_type_with_count_returns_type_colon_count() -> None:
    settings = ModalStepOperatorSettings(gpu="A100")

    rs_two = ResourceSettingsStub(gpu_count=2)
    assert get_gpu_values(settings, rs_two) == "A100:2"

    rs_one = ResourceSettingsStub(gpu_count=1)
    assert get_gpu_values(settings, rs_one) == "A100:1"


def test_gpu_arg_type_with_zero_count_warns_and_returns_cpu_only(
    caplog,
) -> None:
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=0)

    with caplog.at_level("WARNING"):
        result = get_gpu_values(settings, rs)

    assert result is None
    assert "running on CPU only" in caplog.text


def test_create_modal_client_from_credentials_normalizes_values(
    monkeypatch,
) -> None:
    modal_client = ModalClientStub("explicit")
    recorded = []

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded.append((token_id, token_secret))
            return modal_client

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )

    assert (
        sandbox_utils.create_modal_client_from_credentials(
            token_id=" ak-test ",
            token_secret=" as-test ",
        )
        is modal_client
    )
    assert recorded == [("ak-test", "as-test")]


def test_create_modal_client_from_credentials_rejects_partial_pair() -> None:
    with pytest.raises(
        StackComponentInterfaceError,
        match="token_id and token_secret must be configured together",
    ):
        sandbox_utils.create_modal_client_from_credentials(
            token_id="ak-test",
            token_secret=None,
        )


def test_create_modal_client_from_credentials_returns_none_without_pair() -> (
    None
):
    assert (
        sandbox_utils.create_modal_client_from_credentials(
            token_id=None,
            token_secret=None,
        )
        is None
    )


def test_modal_client_preserves_ambient_auth(monkeypatch) -> None:
    recorded = []

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded.append((token_id, token_secret))
            raise AssertionError(
                "Ambient auth must not create an explicit client."
            )

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )

    operator = _make_operator(ModalStepOperatorConfig())

    assert operator._get_modal_client() is None
    assert recorded == []


def test_modal_client_caches_and_rebuilds_explicit_client(
    monkeypatch,
) -> None:
    first_client = ModalClientStub("first")
    second_client = ModalClientStub("second")
    clients = [first_client, second_client]
    recorded = []

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded.append((token_id, token_secret))
            return clients.pop(0)

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )

    operator = _make_operator(
        ModalStepOperatorConfig(
            token_id="ak-test",
            token_secret="as-test",
        )
    )

    assert operator._get_modal_client() is first_client
    assert operator._get_modal_client() is first_client

    first_client.closed = True

    assert operator._get_modal_client() is second_client
    assert recorded == [
        ("ak-test", "as-test"),
        ("ak-test", "as-test"),
    ]


def test_modal_client_returns_open_cache_without_reading_config(
    monkeypatch,
) -> None:
    cached_client = ModalClientStub("cached")

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            raise AssertionError(
                "Cached clients must not create a new explicit client."
            )

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )
    operator = _make_operator(
        ModalStepOperatorConfig(
            token_id="ak-test",
            token_secret="as-test",
        )
    )
    operator._modal_client = cached_client

    monkeypatch.setattr(
        modal_step_operator_module.ModalStepOperator,
        "config",
        property(
            lambda _self: pytest.fail(
                "Open cached clients must be returned before reading config."
            )
        ),
    )

    assert operator._get_modal_client() is cached_client


def test_modal_client_uses_lock_for_concurrent_creation(
    monkeypatch,
) -> None:
    modal_client = ModalClientStub("explicit")
    creation_lock = threading.Lock()
    creation_count = 0

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            nonlocal creation_count
            assert (token_id, token_secret) == ("ak-test", "as-test")
            time.sleep(0.05)
            with creation_lock:
                creation_count += 1
            return modal_client

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )

    operator = _make_operator(
        ModalStepOperatorConfig(
            token_id="ak-test",
            token_secret="as-test",
        )
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        clients = list(
            executor.map(lambda _: operator._get_modal_client(), range(8))
        )

    assert clients == [modal_client] * 8
    assert creation_count == 1


def test_modal_submit_passes_explicit_client_and_runtime_env_boundary(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MODAL_TOKEN_ID", "ambient-token-id")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "ambient-token-secret")
    monkeypatch.setenv("MODAL_ENVIRONMENT", "ambient-environment")

    modal_client = ModalClientStub("explicit")
    recorded, run_metadata, entrypoint_command, environment = (
        _submit_with_stubs(
            monkeypatch=monkeypatch,
            config=ModalStepOperatorConfig(
                token_id="ak-test",
                token_secret="as-test",
            ),
            settings=ModalStepOperatorSettings(
                modal_environment="staging",
                timeout=1234,
            ),
            modal_client=modal_client,
        )
    )

    assert recorded["client_credentials"] == [("ak-test", "as-test")]
    assert recorded["image_name"] == "registry.example.com/zenml:latest"
    assert recorded["image_kwargs"] == {}
    assert recorded["secret_values"] == [
        {SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "sensitive-token"}
    ]
    runtime_secret = recorded["secrets"][0]
    assert recorded["app_lookup"] == (
        ("zenml-step-run-id-train",),
        {
            "create_if_missing": True,
            "environment_name": "staging",
            "client": modal_client,
        },
    )
    assert recorded["sandbox_create"] == (
        tuple(entrypoint_command),
        {
            "app": "app",
            "image": recorded["image"],
            "gpu": None,
            "cpu": 2,
            "memory": 2,
            "cloud": None,
            "region": None,
            "timeout": 1234,
            "env": {"ZENML_ENV": "value"},
            "client": modal_client,
            "secrets": [runtime_secret],
        },
    )
    sandbox_env = recorded["sandbox_create"][1]["env"]
    assert sandbox_env == {"ZENML_ENV": "value"}
    assert SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY not in sandbox_env
    assert environment == {
        "ZENML_ENV": "value",
        "ZENML_STORE_API_TOKEN": "sensitive-token",
    }
    for env_var in (
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "MODAL_ENVIRONMENT",
    ):
        assert env_var not in sandbox_env
    assert os.environ["MODAL_TOKEN_ID"] == "ambient-token-id"
    assert os.environ["MODAL_TOKEN_SECRET"] == "ambient-token-secret"
    assert os.environ["MODAL_ENVIRONMENT"] == "ambient-environment"
    assert "environment_name" not in recorded["sandbox_create"][1]
    expected_metadata = {
        modal_step_operator_module.STEP_SANDBOX_ID_METADATA_KEY: "sandbox-id",
        modal_step_operator_module.STEP_MODAL_ENVIRONMENT_METADATA_KEY: "staging",
    }
    assert recorded["published_metadata"] == (
        ("step-run-id", {"component-id": expected_metadata}),
        {},
    )
    assert run_metadata == expected_metadata


def test_modal_submit_passes_registry_credentials_to_image_from_registry(
    monkeypatch,
) -> None:
    recorded, _, _, _ = _submit_with_stubs(
        monkeypatch=monkeypatch,
        config=ModalStepOperatorConfig(),
        settings=ModalStepOperatorSettings(),
        modal_client=None,
        registry_credentials=("docker-user", "docker-pass"),
        environment={"ZENML_ENV": "value"},
    )

    assert recorded["secret_values"] == [
        {
            "REGISTRY_USERNAME": "docker-user",
            "REGISTRY_PASSWORD": "docker-pass",
        }
    ]
    registry_secret = recorded["secrets"][0]
    assert recorded["image_kwargs"] == {"secret": registry_secret}
    assert recorded["sandbox_create"][1]["env"] == {"ZENML_ENV": "value"}
    assert "secrets" not in recorded["sandbox_create"][1]


def test_modal_submit_terminates_sandbox_when_metadata_publish_fails(
    monkeypatch,
) -> None:
    publish_error = RuntimeError("metadata publish failed")
    recorded, run_metadata, _, _ = _submit_with_stubs(
        monkeypatch=monkeypatch,
        config=ModalStepOperatorConfig(),
        settings=ModalStepOperatorSettings(),
        modal_client=None,
        publish_step_run_metadata_error=publish_error,
        expect_submit_error=True,
    )

    assert recorded["submit_error"] is publish_error
    assert recorded["sandbox"].terminate_calls == 1
    assert "published_metadata" not in recorded
    assert run_metadata == {}


def test_modal_submit_terminates_sandbox_when_local_metadata_update_fails(
    monkeypatch,
) -> None:
    update_error = RuntimeError("local metadata update failed")

    class FailingRunMetadata(dict):
        def update(self, *args, **kwargs):
            raise update_error

    recorded, run_metadata, _, _ = _submit_with_stubs(
        monkeypatch=monkeypatch,
        config=ModalStepOperatorConfig(),
        settings=ModalStepOperatorSettings(),
        modal_client=None,
        run_metadata=FailingRunMetadata(),
        expect_submit_error=True,
    )

    expected_metadata = {
        modal_step_operator_module.STEP_SANDBOX_ID_METADATA_KEY: "sandbox-id"
    }
    assert recorded["submit_error"] is update_error
    assert recorded["published_metadata"] == (
        ("step-run-id", {"component-id": expected_metadata}),
        {},
    )
    assert recorded["sandbox"].terminate_calls == 1
    assert run_metadata == {}


def test_modal_submit_preserves_ambient_auth_with_client_none(
    monkeypatch,
) -> None:
    recorded, _, _, _ = _submit_with_stubs(
        monkeypatch=monkeypatch,
        config=ModalStepOperatorConfig(),
        settings=ModalStepOperatorSettings(
            modal_environment="staging",
            timeout=1234,
        ),
        modal_client=None,
    )

    assert recorded["client_credentials"] == []
    assert recorded["app_lookup"][1]["environment_name"] == "staging"
    assert recorded["app_lookup"][1]["client"] is None
    assert recorded["sandbox_create"][1]["client"] is None
    assert "environment_name" not in recorded["sandbox_create"][1]


def test_status_and_cancel_use_cached_explicit_modal_client(
    monkeypatch,
) -> None:
    modal_client = ModalClientStub("explicit")
    recorded = {"client_credentials": [], "from_id_calls": []}

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded["client_credentials"].append((token_id, token_secret))
            return modal_client

    class SandboxStub:
        def poll(self):
            recorded["poll_called"] = True
            return 0

        def terminate(self):
            recorded["terminate_called"] = True

    class SandboxFactoryStub:
        @staticmethod
        def from_id(sandbox_id, **kwargs):
            recorded["from_id_calls"].append((sandbox_id, kwargs))
            return SandboxStub()

    operator = _make_operator(
        ModalStepOperatorConfig(
            token_id="ak-test",
            token_secret="as-test",
        )
    )
    step_run = SimpleNamespace(
        run_metadata={
            modal_step_operator_module.STEP_SANDBOX_ID_METADATA_KEY: "sandbox-id"
        }
    )

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Sandbox", SandboxFactoryStub
    )

    assert operator.get_status(step_run).value == "completed"
    operator.cancel(step_run)

    assert recorded["client_credentials"] == [("ak-test", "as-test")]
    assert recorded["from_id_calls"] == [
        ("sandbox-id", {"client": modal_client}),
        ("sandbox-id", {"client": modal_client}),
    ]
    assert recorded["poll_called"] is True
    assert recorded["terminate_called"] is True


def test_status_and_cancel_preserve_ambient_auth_with_client_none(
    monkeypatch,
) -> None:
    recorded = {"client_credentials": [], "from_id_calls": []}

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded["client_credentials"].append((token_id, token_secret))
            raise AssertionError(
                "Ambient auth must not create an explicit client."
            )

    class SandboxStub:
        def poll(self):
            return None

        def terminate(self):
            recorded["terminate_called"] = True

    class SandboxFactoryStub:
        @staticmethod
        def from_id(sandbox_id, **kwargs):
            recorded["from_id_calls"].append((sandbox_id, kwargs))
            return SandboxStub()

    operator = _make_operator(ModalStepOperatorConfig())
    step_run = SimpleNamespace(
        run_metadata={
            modal_step_operator_module.STEP_SANDBOX_ID_METADATA_KEY: "sandbox-id"
        }
    )

    monkeypatch.setattr(
        sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Sandbox", SandboxFactoryStub
    )

    assert operator.get_status(step_run).value == "running"
    operator.cancel(step_run)

    assert recorded["client_credentials"] == []
    assert recorded["from_id_calls"] == [
        ("sandbox-id", {"client": None}),
        ("sandbox-id", {"client": None}),
    ]
    assert recorded["terminate_called"] is True


def test_gpu_arg_whitespace_type_treated_as_none_behavior() -> None:
    settings = ModalStepOperatorSettings(gpu="   ")

    # With positive GPU count this should raise since type is treated as None.
    rs_positive = ResourceSettingsStub(gpu_count=2)
    with pytest.raises(StackComponentInterfaceError):
        get_gpu_values(settings, rs_positive)

    # With zero or None count, this should be CPU-only (None).
    rs_zero = ResourceSettingsStub(gpu_count=0)
    assert get_gpu_values(settings, rs_zero) is None

    rs_none = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs_none) is None
