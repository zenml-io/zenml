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

from contextlib import ExitStack as does_not_raise
from typing import Optional

import pytest
from pydantic import BaseModel, ValidationError

from zenml.utils import deprecation_utils


def test_pydantic_model_attribute_deprecation():
    """Tests utility function to deprecate pydantic attributes."""

    class Model(BaseModel):
        deprecated: Optional[str] = None

        old: Optional[str] = None
        new: Optional[str] = None

        _deprecatation_validator = (
            deprecation_utils.deprecate_pydantic_attributes(
                "deprecated", ("old", "new")
            )
        )

    with does_not_raise():
        Model(old="aria", new="aria")
        Model(new="aria")

        m = Model(old="aria")
        assert m.new == "aria"

    with pytest.warns(DeprecationWarning):
        Model(deprecated="aria")

    with pytest.warns(DeprecationWarning):
        Model(old="old_aria")

    with pytest.raises(ValidationError):
        # different value for deprecated and replacement attribute
        Model(old="aria", new="not_aria")

    class InvalidAttributeNameModel(BaseModel):
        deprecated: Optional[str] = None

        _deprecatation_validator = (
            deprecation_utils.deprecate_pydantic_attributes("not_an_attribute")
        )

    with pytest.raises(ValidationError):
        InvalidAttributeNameModel()

    class DeprecateRequiredAttributeModel(BaseModel):
        deprecated: str

        _deprecatation_validator = (
            deprecation_utils.deprecate_pydantic_attributes("deprecated")
        )

    with pytest.raises(TypeError):
        DeprecateRequiredAttributeModel(deprecated="")
