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

from steps import feature_engineering

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    settings={
        "docker": DockerSettings(
            apt_packages=["git"], requirements="requirements.txt"
        )
    }
)
def llm_lora_feature_engineering() -> None:
    """Feature engineering pipeline."""
    feature_engineering()
