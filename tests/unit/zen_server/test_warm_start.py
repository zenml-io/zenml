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
"""Tests for the warm start of a ZenML Pro server."""

import subprocess
import sys
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.zen_server.warm_start import WorkspaceIdentity


def test_loading_server_code_reads_no_settings() -> None:
    """A new read of the settings while loading would keep the wrong values."""
    code = (
        "import sys\n"
        "from zenml.zen_server.warm_start import API_MODULE, load_server_code\n"
        "from zenml.zen_server import utils\n"
        "load_server_code()\n"
        "assert utils._server_config is None\n"
        "assert API_MODULE not in sys.modules\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_identity_refuses_a_claim_without_an_organization() -> None:
    """A server must never finish starting without a customer."""
    with pytest.raises(ValidationError):
        WorkspaceIdentity.model_validate({"claimed": True})


def test_identity_ignores_variables_it_does_not_expect() -> None:
    """Values from the API become environment variables, so only allow some."""
    identity = WorkspaceIdentity.model_validate(
        {
            "claimed": True,
            "organization_id": str(uuid4()),
            "environment": {"LD_PRELOAD": "/tmp/library.so"},
        }
    )
    assert identity.environment == {}
