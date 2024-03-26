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

import importlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from lit_gpt import Config
from materializers.directory_materializer import DirectoryMaterializer
from pydantic import BaseModel
from scripts.download import download_from_hub
from typing_extensions import Annotated

from steps.utils import get_huggingface_access_token
from zenml import log_artifact_metadata, step


class FeatureEngineeringParameters(BaseModel):
    """Parameters for the feature engineering step."""

    model_repo: str
    dataset_name: str

    prepare_kwargs: Dict[str, Any] = {}


@step(output_materializers=DirectoryMaterializer)
def feature_engineering(
    config: FeatureEngineeringParameters,
) -> Annotated[Path, "dataset"]:
    """Prepare the dataset.

    Args:
        config: Configuration for this step.
    """
    access_token = get_huggingface_access_token()

    checkpoint_root_dir = Path("checkpoints")
    download_from_hub(
        repo_id=config.model_repo,
        tokenizer_only=True,
        checkpoint_dir=checkpoint_root_dir,
        access_token=access_token,
    )

    checkpoint_dir = checkpoint_root_dir / config.model_repo

    model_name = checkpoint_dir.name
    lit_config = Config.from_name(model_name)
    lit_config_dict = asdict(lit_config)
    with open(checkpoint_dir / "lit_config.json", "w") as json_config:
        json.dump(lit_config_dict, json_config)

    log_artifact_metadata(
        metadata={
            "model_name": model_name,
            "model_config": lit_config_dict,
            "dataset_name": config.dataset_name,
        }
    )
    destination_dir = Path("data") / config.dataset_name

    helper_module = importlib.import_module(
        f"scripts.prepare_{config.dataset_name}"
    )
    prepare_function = getattr(helper_module, "prepare")

    prepare_function(
        checkpoint_dir=checkpoint_dir,
        destination_path=destination_dir,
        **config.prepare_kwargs,
    )
    return destination_dir
