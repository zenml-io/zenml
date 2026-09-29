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
from typing import Any

import pytest

from zenml.artifacts.in_memory_cache import InMemoryArtifactCache


class AmbiguousTruthValue:
    """Artifact data that cannot be evaluated in a boolean context.

    This mirrors types like `pandas.DataFrame` and `numpy.ndarray`.
    """

    def __bool__(self) -> bool:
        raise ValueError("The truth value is ambiguous.")


@pytest.fixture
def materialize(mocker):
    """Replace artifact materialization with a controllable mock."""

    def _materialize(*return_values: Any):
        return mocker.patch(
            "zenml.artifacts.utils.load_artifact_from_response",
            side_effect=list(return_values),
        )

    return _materialize


def test_load_does_not_evaluate_the_truthiness_of_artifact_data(
    materialize, sample_artifact_version_model
):
    data = AmbiguousTruthValue()
    load = materialize(data)

    with InMemoryArtifactCache():
        assert sample_artifact_version_model.load() is data
        assert sample_artifact_version_model.load() is data

    load.assert_called_once()


@pytest.mark.parametrize("data", [None, 0], ids=repr)
def test_load_caches_falsy_artifact_data(
    materialize, sample_artifact_version_model, data
):
    load = materialize(data)

    with InMemoryArtifactCache():
        assert sample_artifact_version_model.load() is data
        assert sample_artifact_version_model.load() is data

    load.assert_called_once()


def test_load_with_a_disabled_cache_bypasses_the_cache(
    materialize, sample_artifact_version_model
):
    cached, reloaded = object(), object()
    materialize(cached, reloaded)

    with InMemoryArtifactCache() as cache:
        assert sample_artifact_version_model.load() is cached
        assert (
            sample_artifact_version_model.load(disable_cache=True) is reloaded
        )
        assert (
            cache.get_artifact_data(sample_artifact_version_model.id) is cached
        )


def test_load_without_an_active_cache_materializes_every_time(
    materialize, sample_artifact_version_model
):
    first, second = object(), object()
    materialize(first, second)

    assert sample_artifact_version_model.load() is first
    assert sample_artifact_version_model.load() is second
