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

from tests.integration.examples.utils import run_example


# TODO: investigate why it is failing with
# FAILED tests/integration/examples/test_tensorflow.py::test_example
# - subprocess.CalledProcessError: Command
# '['/home/runner/_work/_tool/Python/3.10.14/x64/bin/python3',
# '/tmp/pytest-of-runner/pytest-0/pytest-zenml-repo6/run.py']'
# died with <Signals.SIGABRT: 6>.
@pytest.mark.skip(
    reason="TensorFlow is not fully compatible with Pydantic 2 requirements",
)
def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the tensorflow example.

    Args:
        request: Factory to generate temporary test paths.
    """
    name = "tensorflow"
    with run_example(
        request=request,
        name=name,
        pipelines={"mnist_pipeline": (1, 4)},
    ):
        pass
