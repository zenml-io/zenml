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
from typing import Dict, List, Set

from numpy import ndarray

from zenml.steps.utils import resolve_type_annotation


def test_type_annotation_resolving():
    """Tests that resolving type annotations works as expected."""
    assert resolve_type_annotation(Dict) is dict
    assert resolve_type_annotation(List[int]) is list
    assert resolve_type_annotation(Set[str]) is set

    assert resolve_type_annotation(set) is set
    assert resolve_type_annotation(ndarray) is ndarray
