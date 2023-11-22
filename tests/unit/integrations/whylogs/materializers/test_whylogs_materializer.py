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
from datetime import datetime

from whylogs.core import DatasetProfileView

from tests.unit.test_general import _test_materializer
from zenml.integrations.whylogs.materializers.whylogs_materializer import (
    WhylogsMaterializer,
)


def test_whylogs_materializer(clean_client):
    """Tests whether the steps work for the Whylogs materializer."""
    dataset_profile_view = _test_materializer(
        step_output=DatasetProfileView(
            columns={},
            dataset_timestamp=datetime.now(),
            creation_timestamp=datetime.now(),
        ),
        materializer_class=WhylogsMaterializer,
        expected_metadata_size=1,
        assert_visualization_exists=True,
    )

    assert dataset_profile_view.creation_timestamp is not None
    assert dataset_profile_view.dataset_timestamp is not None
    assert datetime.now() > dataset_profile_view.creation_timestamp
    assert datetime.now() > dataset_profile_view.dataset_timestamp
