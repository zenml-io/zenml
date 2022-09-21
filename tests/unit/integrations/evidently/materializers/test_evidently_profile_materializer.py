#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of Evidently profile materializer."""
from contextlib import ExitStack as does_not_raise

from evidently.model_profile import Profile
from evidently.model_profile.sections import DataDriftProfileSection

from tests.unit.test_general import _test_materializer
from zenml.integrations.evidently.materializers.evidently_profile_materializer import (
    EvidentlyProfileMaterializer,
)


def test_evidently_profile_materializer(clean_repo):
    """Test the Evidently profile materializer."""
    with does_not_raise():
        _test_materializer(
            step_output=Profile(sections=[DataDriftProfileSection()]),
            materializer=EvidentlyProfileMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    evidently_profile = last_run.steps[-1].output.read()
    assert isinstance(evidently_profile, Profile)
