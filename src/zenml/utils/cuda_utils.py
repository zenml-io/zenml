# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Utilities for managing GPU memory."""

import gc

from zenml.logger import get_logger

logger = get_logger(__name__)


def cleanup_gpu_memory(force: bool = False) -> None:
    """Clean up GPU memory.

    Args:
        force: whether to force the cleanup of GPU memory (must be passed explicitly)
    """
    if not force:
        logger.warning(
            "This will clean up all GPU memory on current physical machine. "
            "This action is considered to be dangerous by default, since "
            "it might affect other processes running in the same environment. "
            "If this is intended, please explicitly pass `force=True`."
        )
    else:
        try:
            import torch
        except ModuleNotFoundError:
            logger.warning(
                "No PyTorch installed. Skipping GPU memory cleanup."
            )
            return

        logger.info("Cleaning up GPU memory...")
        while gc.collect():
            torch.cuda.empty_cache()
