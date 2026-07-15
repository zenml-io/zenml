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
"""Locate and register the trainer's checkpoint output."""

from pathlib import Path
from typing import Optional

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def find_checkpoint(output_dir: str) -> Optional[str]:
    """Find the newest HF-format weight snapshot the trainer emitted.

    prime-rl writes servable HF-format weights to
    ``<output_dir>/weights/step_N`` (enabled by ``--ckpt``). The path is
    recorded as metadata and returned rather than uploaded: full-model
    weight dirs dominate a run's bytes, so shipping them into the
    artifact store is a deliberate, separate decision — on shared
    storage the path IS the artifact.

    Args:
        output_dir: The prime-rl output directory.

    Returns:
        The newest ``weights/step_N`` directory as a string, or None if
        the run produced no weight snapshot (e.g. ``--ckpt`` not set).
    """
    weights_root = Path(output_dir) / "weights"
    if not weights_root.is_dir():
        logger.warning(
            "No weights directory under %s — did the trainer run with --ckpt?",
            output_dir,
        )
        return None
    candidates = sorted(
        (path for path in weights_root.glob("step_*") if path.is_dir()),
        key=lambda path: int(path.name.removeprefix("step_") or -1),
    )
    if not candidates:
        logger.warning("weights/ exists but holds no step_N dirs.")
        return None
    newest = candidates[-1]
    log_metadata(
        metadata={
            "checkpoint.path": str(newest),
            "checkpoint.step": int(newest.name.removeprefix("step_")),
            "checkpoint.format": "hf",
        }
    )
    return str(newest)
