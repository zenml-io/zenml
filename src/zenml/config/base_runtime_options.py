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
"""Base class for all ZenML runtime options."""
from enum import IntFlag, auto
from typing import Any, ClassVar, Dict, Optional, Union

from pydantic import Extra

from zenml.config.secret_reference_mixin import SecretReferenceMixin

RuntimeOptionsOrDict = Union[Dict[str, Any], "BaseRuntimeOptions"]


class ConfigurationLevel(IntFlag):
    """Runtime options configuration level."""

    STEP = auto()
    PIPELINE = auto()


class BaseRuntimeOptions(SecretReferenceMixin):
    """Base class for runtime options."""

    KEY: ClassVar[Optional[str]] = None
    LEVEL: ClassVar[ConfigurationLevel] = (
        ConfigurationLevel.PIPELINE | ConfigurationLevel.STEP
    )

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # allow extra attributes so this class can be used to parse dicts
        # of arbitrary subclasses
        extra = Extra.allow
