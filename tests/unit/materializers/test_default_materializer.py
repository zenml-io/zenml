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


from tempfile import TemporaryDirectory

from tests.unit.test_general import _test_materializer
from zenml.environment import Environment
from zenml.materializers.default_materializer import DefaultMaterializer


class Unmaterializable:
    """A class that has no materializer."""

    cat = "aria"


def test_default_materializer(clean_client):
    """Test whether the default materializer is used if no other is found."""
    output = _test_materializer(
        step_output=Unmaterializable(), expected_metadata_size=1
    )
    assert output.cat == "aria"


def test_default_materializer_python_version_check(clean_client):
    """Test that the default materializer saves the correct Python version."""
    with TemporaryDirectory() as artifact_uri:
        materializer = DefaultMaterializer(uri=artifact_uri)
        materializer._save_python_version()
        version = materializer._load_python_version()
        assert version == Environment().python_version()
