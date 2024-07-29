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
import pytest

from zenml.utils.package_utils import clean_requirements


@pytest.mark.parametrize(
    "input_reqs, expected_output",
    [
        (
            ["package1==1.0.0", "package2>=2.0.0", "package3<3.0.0"],
            ["package1==1.0.0", "package2>=2.0.0", "package3<3.0.0"],
        ),
        (
            ["package1==1.0.0", "package1==2.0.0", "package2>=2.0.0"],
            ["package1==2.0.0", "package2>=2.0.0"],
        ),
        (
            ["package1[extra]==1.0.0", "package2[test,dev]>=2.0.0"],
            ["package1[extra]==1.0.0", "package2[test,dev]>=2.0.0"],
        ),
        (
            [
                "package1",
                "package2==2.0.0",
                "package1>=1.5.0",
                "package3<3.0.0",
            ],
            ["package1>=1.5.0", "package2==2.0.0", "package3<3.0.0"],
        ),
        ([], []),
        (
            ["package1~=1.0.0", "package2^=2.0.0", "package3==3.0.0"],
            ["package1~=1.0.0", "package2^=2.0.0", "package3==3.0.0"],
        ),
        (
            ["package1~=1.0.0", "package1^=1.1.0", "package1==1.2.0"],
            ["package1==1.2.0"],
        ),
        (["package1", "package1~=1.0.0"], ["package1~=1.0.0"]),
    ],
)
def test_clean_requirements(input_reqs, expected_output):
    """Test clean_requirements function."""
    assert clean_requirements(input_reqs) == expected_output


def test_clean_requirements_type_error():
    """Test clean_requirements function with wrong input type."""
    with pytest.raises(TypeError):
        clean_requirements("not a list")


def test_clean_requirements_value_error():
    """Test clean_requirements function with wrong input value."""
    with pytest.raises(ValueError):
        clean_requirements([1, 2, 3])  # List of non-string elements


def test_clean_requirements_mixed_types():
    """Test clean_requirements function with mixed types in list."""
    with pytest.raises(ValueError):
        clean_requirements(["package1==1.0.0", 2, "package3<3.0.0"])
