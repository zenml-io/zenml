#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.backends import BaseBackend
from zenml.steps import BaseStep


def test_to_from_config(equal_steps):
    kwargs = {"a": 1, "name": "my_backend", "grade": 1.5}
    s1 = BaseStep(**kwargs)

    s2 = BaseStep.from_config(s1.to_config())

    assert equal_steps(s1, s2, loaded=True)


def test_with_backend(equal_steps):
    kwargs = {"a": 1, "name": "my_backend", "grade": 1.5}

    b1 = BaseBackend(**kwargs)

    s1 = BaseStep(**kwargs).with_backend(b1)

    assert bool(s1.backend)

    s2 = BaseStep.from_config(s1.to_config())

    assert equal_steps(s1, s2, loaded=True)
