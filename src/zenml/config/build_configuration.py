#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Dict, Optional

from pydantic import BaseModel

from zenml.config import DockerSettings


class BuildConfiguration(BaseModel):
    key: str
    settings: DockerSettings
    tag: str
    step_name: Optional[str] = None
    entrypoint: Optional[str] = None
    extra_files: Dict[str, str] = {}

    @property
    def settings_hash(self) -> str:
        import hashlib

        build_settings_hash = hashlib.md5()
        build_settings_hash.update(self.settings.json().encode())
        if self.entrypoint:
            build_settings_hash.update(self.entrypoint.encode())

        for destination, source in self.extra_files.items():
            build_settings_hash.update(destination.encode())
            build_settings_hash.update(source.encode())

        return build_settings_hash.hexdigest()
