from zenml.integrations.modal import MODAL_STEP_OPERATOR_FLAVOR
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    DEFAULT_TIMEOUT_SECONDS,
    ModalStepOperatorConfig,
    ModalStepOperatorFlavor,
    ModalStepOperatorSettings,
)


def test_modal_settings_default_timeout() -> None:
    settings = ModalStepOperatorSettings()
    assert settings.timeout == DEFAULT_TIMEOUT_SECONDS


def test_modal_config_is_remote_true() -> None:
    cfg = ModalStepOperatorConfig()
    assert cfg.is_remote is True


def test_modal_flavor_name_constant() -> None:
    flavor = ModalStepOperatorFlavor()
    assert flavor.name == MODAL_STEP_OPERATOR_FLAVOR
