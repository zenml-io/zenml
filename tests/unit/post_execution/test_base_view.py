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
"""Tests for the base view class."""

from datetime import datetime
from typing import Tuple, cast
from uuid import uuid4

import pytest

from zenml.models.base_models import BaseResponseModel
from zenml.post_execution.base_view import BaseView


class AriaResponseModel(BaseResponseModel):
    """Response model class that is used in the test view below."""

    name: str = "Aria"
    is_cat: bool = True


class AriaView(BaseView):
    """View class for testing."""

    MODEL_CLASS = AriaResponseModel
    REPR_KEYS = ["name", "belongs_to_alex"]

    def model(self) -> AriaResponseModel:
        return cast(AriaResponseModel, self._model)

    @property
    def belongs_to_alex(self) -> bool:
        return True

    @property
    def is_cat(self) -> bool:
        return False  # She's a family member, not a cat.


@pytest.fixture
def looking_at_aria() -> Tuple[AriaResponseModel, AriaView]:
    """Fixture that returns a model and view for Aria."""
    aria_model = AriaResponseModel(
        id=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    aria_view = AriaView(aria_model)
    return aria_model, aria_view


def test_model_fields_are_accessible(looking_at_aria):
    """Test that non-overridden model fields are accessible on the view."""
    aria_model, aria_view = looking_at_aria
    assert aria_view.id == aria_model.id
    assert aria_view.created == aria_model.created
    assert aria_view.updated == aria_model.updated
    assert aria_view.name == aria_model.name


def test_view_attributes_are_accessible(looking_at_aria):
    """Test that additional view attributes are accessible."""
    _, aria = looking_at_aria
    assert aria.belongs_to_alex


def test_view_properties_override_model_fields(looking_at_aria):
    """Test that view properties override model fields."""
    _, aria = looking_at_aria
    assert aria.is_cat is False


def test_repr(looking_at_aria):
    """Test that the repr is correct."""
    _, aria = looking_at_aria
    # We expect only `name` and `belongs_to_alex` to be in the repr.
    assert repr(aria) == "AriaView(name=Aria, belongs_to_alex=True)"


def test_invalid_repr_keys_raise_error(looking_at_aria):
    """Test that invalid repr keys raise an error."""
    aria_model, _ = looking_at_aria

    with pytest.raises(ValueError):

        class InvalidView(BaseView):
            MODEL_CLASS = AriaResponseModel
            REPR_KEYS = ["not_a_field"]

            def model(self) -> AriaResponseModel:
                return cast(AriaResponseModel, self._model)

        InvalidView(aria_model)


class BlupusResponseModel(BaseResponseModel):
    """A model of Blupus, who is not Aria."""

    name: str = "Blupus"
    is_cat: bool = True


class BlupusView(AriaView):
    """A view of Blupus, who is not Aria.

    Exact same implementation except for the model class.
    """

    MODEL_CLASS = BlupusResponseModel

    def model(self) -> BlupusResponseModel:
        return cast(BlupusResponseModel, self._model)


@pytest.fixture
def looking_at_blupus() -> Tuple[BlupusResponseModel, BaseView]:
    """Fixture that returns a model and view for Blupus."""
    blupus_model = BlupusResponseModel(
        id=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    blupus_view = BlupusView(blupus_model)
    return blupus_model, blupus_view


def test_initializing_view_with_wrong_model_fails(
    looking_at_aria, looking_at_blupus
):
    """Test that initializing a view with the wrong model fails."""
    aria_model, _ = looking_at_aria
    blupus_model, _ = looking_at_blupus
    with pytest.raises(TypeError):
        AriaView(blupus_model)
    with pytest.raises(TypeError):
        BlupusView(aria_model)


def test_eq(looking_at_aria, looking_at_blupus):
    """Test that equality works by comparing the underlying models."""
    aria_model, aria_view = looking_at_aria
    blupus_model, blupus_view = looking_at_blupus
    assert aria_view == aria_view
    assert AriaView(aria_model) == aria_view
    assert blupus_view == blupus_view
    assert BlupusView(blupus_model) == blupus_view
    assert (aria_view == blupus_view) == (aria_model == blupus_model)
