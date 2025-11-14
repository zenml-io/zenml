#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the PyTorch Module materializer (with SafeTensors)."""

from __future__ import annotations

import importlib
import json
import os
import tempfile
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
    cast,
)

import cloudpickle  # for legacy entire_model.pt compatibility
import torch
from torch.nn import Module

from zenml.enums import ArtifactType
from zenml.integrations.pytorch.materializers.base_pytorch_materializer import (
    BasePyTorchMaterializer,
)
from zenml.integrations.pytorch.utils import count_module_params
from zenml.logger import get_logger
from zenml.utils.io_utils import copy_dir

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)

# Legacy names kept for compatibility (we no longer write these in Phase 1).
DEFAULT_FILENAME = "entire_model.pt"
CHECKPOINT_FILENAME = "checkpoint.pt"

# New filenames for Phase 1
WEIGHTS_SAFE = "weights.safetensors"
WEIGHTS_PT = "weights.pt"
META_FILE = "metadata.json"


def _import_from_path(class_path: str) -> Type[Any]:
    """Import a class from 'pkg.module:Class' or 'pkg.module.Class'.
    
    Args:
        class_path: Fully qualified class path.
        
    Returns:
        The imported class.
    """
    if ":" in class_path:
        mod, cls = class_path.split(":")
    else:
        parts = class_path.split(".")
        mod, cls = ".".join(parts[:-1]), parts[-1]
    module = importlib.import_module(mod)
    return cast(Type[Any], getattr(module, cls))


def _has_safetensors() -> bool:
    try:
        import safetensors.torch  # noqa: F401

        return True
    except Exception:
        return False


class PyTorchModuleMaterializer(BasePyTorchMaterializer):
    """Materializer to read/write PyTorch models."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Module,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    # NOTE: FILENAME is unused in Phase 1 (we don't write entire_model.pt)
    FILENAME: ClassVar[str] = DEFAULT_FILENAME

    # ---------------------------
    # Save
    # ---------------------------
    def save(self, model: Module) -> None:
        """Save a PyTorch model as state_dict + metadata.

        Why: prefer non-pickle format (safetensors) for security and speed.
        If safetensors is missing, fall back to .pt (pickle) with a warning.
        Use a local temp dir then copy to artifact store to satisfy PathLike I/O.
        """
        # Build a CPU-mapped state_dict to ensure portability across devices.
        state_dict = {
            k: v.detach().cpu() for k, v in model.state_dict().items()
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = os.path.abspath(tmp)

            # Write weights
            if _has_safetensors():
                from safetensors.torch import save_file

                weights_path = os.path.join(tmp_dir, WEIGHTS_SAFE)
                save_file(state_dict, weights_path)
                fmt = "safetensors"
            else:
                logger.warning(
                    "safetensors not installed; falling back to pickle (.pt). "
                    "Install with: pip install 'zenml[safetensors]'"
                )
                weights_path = os.path.join(tmp_dir, WEIGHTS_PT)
                # NOTE: torch.save uses pickle; fallback intended for trusted environments.
                torch.save(state_dict, weights_path, pickle_module=cloudpickle)  # nosec
                fmt = "pickle"

            # Write minimal metadata (extensible in future phases)
            meta: Dict[str, Any] = {
                "class_path": f"{model.__class__.__module__}.{model.__class__.__name__}",
                "serialization_format": fmt,
                # Reserved (Phase 2+)
                "init_args": [],
                "init_kwargs": {},
                "factory_path": None,
            }
            with open(os.path.join(tmp_dir, META_FILE), "w") as f:
                json.dump(meta, f, indent=2)

            # Upload directory to artifact store (remote-safe)
            copy_dir(tmp_dir, self.uri)

        # IMPORTANT:
        # We intentionally do NOT call super().save(model) nor write CHECKPOINT_FILENAME
        # to avoid duplicate / insecure pickle artifacts in Phase 1.

    # ---------------------------
    # Load
    # ---------------------------
    def load(self, data_type: Optional[Type[Module]] = None) -> Module:
        """Load a PyTorch model and always return nn.Module.

        Rules:
          - Phase 1: require zero-arg constructor when metadata is present.
          - Legacy (.pt only, no metadata): require `data_type` to be provided.
          - Raise clear exceptions when reconstruction is not possible.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = os.path.abspath(tmp)

            # Mirror artifact dir locally for PathLike-only APIs
            copy_dir(self.uri, tmp_dir)

            meta_path = os.path.join(tmp_dir, META_FILE)
            has_meta = os.path.exists(meta_path)

            if has_meta:
                # New format (metadata-driven)
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                class_path = meta.get("class_path")
                if not class_path:
                    raise ValueError("metadata.json missing 'class_path'")

                try:
                    model_class = cast(
                        Type[Module], _import_from_path(class_path)
                    )
                except (ImportError, AttributeError) as e:
                    raise ImportError(
                        f"Cannot import model class '{class_path}': {e}. "
                        "Ensure the module/package is available in PYTHONPATH."
                    ) from e

                fmt = meta.get("serialization_format", "pickle")
            else:
                legacy_entire_model = os.path.join(tmp_dir, DEFAULT_FILENAME)
                if os.path.exists(legacy_entire_model):
                    model = torch.load(
                        legacy_entire_model,
                        map_location="cpu",
                        weights_only=False,
                    )
                    if not isinstance(model, Module):
                        raise RuntimeError(
                            f"Legacy file {DEFAULT_FILENAME} did not contain "
                            "a torch.nn.Module."
                        )
                    model.eval()
                    return model

                logger.warning(
                    "No metadata.json found. Loading legacy artifact: "
                    "using `data_type` parameter for model class."
                )
                if data_type is None:
                    raise FileNotFoundError(
                        "Legacy artifact without metadata.json requires "
                        "`data_type` (the model class) to reconstruct."
                    )
                model_class = data_type
                fmt = "pickle"  # legacy assumption

            # Load weights or legacy entire model
            if fmt == "safetensors":
                safetensors_path = os.path.join(tmp_dir, WEIGHTS_SAFE)
                if not os.path.exists(safetensors_path):
                    raise FileNotFoundError(f"Expected {safetensors_path} not found.")
                try:
                    from safetensors.torch import load_file
                except ImportError as e:
                    raise ImportError(
                        "This artifact was saved with 'safetensors', but the optional "
                        "dependency is not installed. Install via:\n"
                        "  pip install 'zenml[safetensors]'"
                    ) from e
                state_dict = load_file(safetensors_path)
            else:
                # pickle/pt - state_dict checkpoints
                pt_candidates = [
                    os.path.join(tmp_dir, WEIGHTS_PT),
                    os.path.join(tmp_dir, CHECKPOINT_FILENAME),
                ]
                pt_path = next((p for p in pt_candidates if os.path.exists(p)), None)
                if not pt_path:
                    raise FileNotFoundError(f"Expected one of {pt_candidates} not found.")
                state_dict = torch.load(pt_path, map_location="cpu")

            # Reconstruct model (Phase 1: zero-arg)
            try:
                model = model_class()
            except TypeError as e:
                raise RuntimeError(
                    f"Failed to instantiate {model_class.__name__}: {e}. "
                    "Phase 1 supports only zero-argument __init__(). "
                    "Use a factory or wait for Phase 2 enhancement."
                ) from e

            try:
                model.load_state_dict(state_dict, strict=True)
            except Exception as e:
                raise RuntimeError(f"Failed to load state_dict: {e}") from e

            model.eval()
            return model

    # ---------------------------
    # Metadata extraction (unchanged)
    # ---------------------------
    def extract_metadata(self, model: Module) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Model` object."""
        return {**count_module_params(model)}
