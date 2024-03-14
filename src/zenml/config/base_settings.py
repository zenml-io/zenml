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
"""Base class for all ZenML settings."""

from enum import IntFlag, auto
from typing import Any, ClassVar, Dict, Union

from pydantic import ConfigDict

from zenml.config.secret_reference_mixin import SecretReferenceMixin

SettingsOrDict = Union[Dict[str, Any], "BaseSettings"]


class ConfigurationLevel(IntFlag):
    """Settings configuration level.

    Bit flag that can be used to specify where a `BaseSettings` subclass
    can be specified.
    """

    STEP = auto()
    PIPELINE = auto()


class BaseSettings(SecretReferenceMixin):
    """Base class for settings.

    The `LEVEL` class variable defines on which level the settings can be
    specified. By default, subclasses can be defined on both pipelines and
    steps.
    """

    LEVEL: ClassVar[ConfigurationLevel] = (
        ConfigurationLevel.PIPELINE | ConfigurationLevel.STEP
    )

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # allow extra attributes so this class can be used to parse dicts
        # of arbitrary subclasses
        extra="allow",
    )
