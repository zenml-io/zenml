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
"""Helpers for constructing a Click ``CliRunner`` across click versions."""

import inspect
from typing import Any

from click.testing import CliRunner

# click 8.2 removed the ``mix_stderr`` parameter and unconditionally
# separates stderr from stdout. Older supported versions still accept (and
# default to mixing) the streams, so we pass ``mix_stderr=False`` only when the
# parameter exists.
_CLI_RUNNER_SUPPORTS_MIX_STDERR = (
    "mix_stderr" in inspect.signature(CliRunner.__init__).parameters
)


def cli_runner(**kwargs: Any) -> CliRunner:
    """Create a CliRunner with stderr separated from stdout."""
    if _CLI_RUNNER_SUPPORTS_MIX_STDERR:
        kwargs.setdefault("mix_stderr", False)
    else:
        kwargs.pop("mix_stderr", None)

    return CliRunner(**kwargs)
