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

import os
from pathlib import Path
from typing import Optional

from scripts.convert_hf_checkpoint import convert_hf_checkpoint

from zenml.client import Client


def get_huggingface_access_token() -> Optional[str]:
    """Get access token for huggingface.

    Returns:
        The access token if one was found.
    """
    try:
        return (
            Client()
            .get_secret("huggingface_credentials")
            .secret_values["token"]
        )
    except KeyError:
        return os.getenv("HF_TOKEN")


def convert_to_lit_checkpoint_if_necessary(checkpoint_dir: Path) -> None:
    """Convert an HF checkpoint to a lit checkpoint if necessary.

    Args:
        checkpoint_dir: The directory of the HF checkpoint.
    """
    lit_model_path = checkpoint_dir / "lit_model.pth"

    if lit_model_path.is_file():
        return

    convert_hf_checkpoint(checkpoint_dir=checkpoint_dir)
