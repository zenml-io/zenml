import pytest

# Skip this entire module if the optional dependency isn't available, because
# the module under test imports `modal` at import time.
pytest.importorskip("modal")

from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.modal.flavors import ModalStepOperatorSettings
from zenml.integrations.modal.step_operators.modal_step_operator import (
    ModalStepOperator,
)


class ResourceSettingsStub:
    """Minimal stub to simulate ZenML ResourceSettings for GPU tests.

    We only model the `gpu_count` attribute because that's the only part the
    helper uses. This keeps tests lightweight and avoids wider dependencies.
    """

    def __init__(self, gpu_count):
        self.gpu_count = gpu_count


def _make_operator() -> ModalStepOperator:
    # Bypass BaseStepOperator initialization since we only need the helper.
    return ModalStepOperator.__new__(ModalStepOperator)


def test_gpu_arg_none_when_no_type_and_no_count() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=None)
    assert op._compute_modal_gpu_arg(settings, rs) is None


def test_gpu_arg_raises_when_count_without_type() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=1)
    with pytest.raises(StackComponentInterfaceError) as e:
        op._compute_modal_gpu_arg(settings, rs)
    assert (
        "GPU resources requested (gpu_count > 0) but no GPU type was specified"
        in str(e.value)
    )


def test_gpu_arg_type_with_no_count_returns_type() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=None)
    assert op._compute_modal_gpu_arg(settings, rs) == "A100"


def test_gpu_arg_type_with_count_returns_type_colon_count() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="A100")

    rs_two = ResourceSettingsStub(gpu_count=2)
    assert op._compute_modal_gpu_arg(settings, rs_two) == "A100:2"

    rs_one = ResourceSettingsStub(gpu_count=1)
    assert op._compute_modal_gpu_arg(settings, rs_one) == "A100:1"


def test_gpu_arg_type_with_zero_count_warns_and_defaults_to_single_gpu(
    caplog,
) -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=0)

    with caplog.at_level("WARNING"):
        result = op._compute_modal_gpu_arg(settings, rs)

    assert result == "A100"
    assert "Defaulting to 1 GPU" in caplog.text


def test_gpu_arg_invalid_negative_count_raises() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="T4")
    rs = ResourceSettingsStub(gpu_count=-1)
    with pytest.raises(StackComponentInterfaceError) as e:
        op._compute_modal_gpu_arg(settings, rs)
    assert "Invalid GPU count" in str(e.value)


def test_gpu_arg_non_integer_count_raises() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="T4")
    rs = ResourceSettingsStub(gpu_count="two")
    with pytest.raises(StackComponentInterfaceError) as e:
        op._compute_modal_gpu_arg(settings, rs)
    assert "Invalid GPU count" in str(e.value)


def test_gpu_arg_whitespace_type_treated_as_none_behavior() -> None:
    op = _make_operator()
    settings = ModalStepOperatorSettings(gpu="   ")

    # With positive GPU count this should raise since type is treated as None.
    rs_positive = ResourceSettingsStub(gpu_count=2)
    with pytest.raises(StackComponentInterfaceError):
        op._compute_modal_gpu_arg(settings, rs_positive)

    # With zero or None count, this should be CPU-only (None).
    rs_zero = ResourceSettingsStub(gpu_count=0)
    assert op._compute_modal_gpu_arg(settings, rs_zero) is None

    rs_none = ResourceSettingsStub(gpu_count=None)
    assert op._compute_modal_gpu_arg(settings, rs_none) is None
