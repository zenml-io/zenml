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

"""Regression tests for import cycles."""

import subprocess
import sys


def test_client_import_does_not_load_public_api_cycle() -> None:
    """Importing the client in a fresh process should not hit a partial module."""
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import zenml.client; import zenml.utils.source_utils",
        ],
        check=True,
    )
