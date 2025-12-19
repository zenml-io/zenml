"""Tests for the PyTorch module materializer."""

from pathlib import Path

import pytest
import torch
from torch import nn

from zenml.integrations.pytorch.materializers.pytorch_module_materializer import (
    DEFAULT_FILENAME,
    META_FILE,
    WEIGHTS_PT,
    WEIGHTS_SAFE,
    PyTorchModuleMaterializer,
)


def _has_safetensors() -> bool:
    """Return True if the optional safetensors dependency is installed."""
    try:
        import safetensors.torch  # noqa

        return True
    except Exception:
        return False


class Tiny(nn.Module):
    """Single linear layer used to validate serialization round-trips."""

    def __init__(self) -> None:
        """Initialize the linear layer used for tests."""
        super().__init__()
        self.fc = nn.Linear(4, 3)


@pytest.mark.skipif(not _has_safetensors(), reason="safetensors is optional")
def test_round_trip_with_safetensors(tmp_path: Path) -> None:
    """End-to-end save/load using safetensors artifacts."""
    m = Tiny()
    mat = PyTorchModuleMaterializer(uri=str(tmp_path))
    mat.save(m)

    # new artifacts exist
    assert (tmp_path / META_FILE).exists()
    assert (tmp_path / WEIGHTS_SAFE).exists()
    # no legacy outputs
    assert not (tmp_path / "checkpoint.pt").exists()
    assert not (tmp_path / "entire_model.pt").exists()
    assert not (tmp_path / WEIGHTS_PT).exists()

    loaded = mat.load()
    assert isinstance(loaded, nn.Module)
    assert isinstance(loaded, Tiny)


def test_legacy_weights_pt_without_metadata(tmp_path: Path) -> None:
    """Legacy state_dict artifacts require passing data_type."""
    # simulate old artifact: weights.pt only, no metadata
    state_dict = Tiny().state_dict()
    torch.save(state_dict, tmp_path / WEIGHTS_PT)
    mat = PyTorchModuleMaterializer(uri=str(tmp_path))

    # must fail without data_type
    with pytest.raises(FileNotFoundError):
        mat.load()

    # works with data_type
    loaded = mat.load(data_type=Tiny)
    assert isinstance(loaded, Tiny)


def test_legacy_entire_model_pt_direct_load(tmp_path: Path) -> None:
    """Very old pickle artifacts still deserialize to nn.Module."""
    # simulate very old artifact: entire_model.pt (pickled Module)
    torch.save(Tiny(), tmp_path / DEFAULT_FILENAME)
    mat = PyTorchModuleMaterializer(uri=str(tmp_path))
    loaded = mat.load()  # metadata-less path returns Module directly
    assert isinstance(loaded, Tiny)


def test_missing_safetensors_dependency_raises_clear_error(
    tmp_path: Path, monkeypatch
) -> None:
    """Missing dependency should produce actionable ImportError."""
    if not _has_safetensors():
        pytest.skip(
            "safetensors not installed; scenario covered by other tests"
        )

    # create safetensors artifact
    m = Tiny()
    mat = PyTorchModuleMaterializer(uri=str(tmp_path))
    mat.save(m)

    # simulate missing dependency at load time
    import sys

    monkeypatch.setitem(sys.modules, "safetensors", None)
    monkeypatch.setitem(sys.modules, "safetensors.torch", None)
    with pytest.raises(ImportError) as e:
        mat.load()
    assert "pip install 'zenml[safetensors]'" in str(e.value)
