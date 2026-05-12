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

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dashboard_utils_does_not_import_client_at_module_scope() -> None:
    """Dashboard utilities should not import the client during module import."""
    source = (REPO_ROOT / "src/zenml/utils/dashboard_utils.py").read_text()
    tree = ast.parse(source)

    assert not any(
        isinstance(statement, ast.ImportFrom)
        and statement.module == "zenml.client"
        for statement in tree.body
    )
