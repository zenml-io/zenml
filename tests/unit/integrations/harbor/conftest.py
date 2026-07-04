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
"""Guard for this test directory's import layout.

This directory must NOT contain an ``__init__.py``: because the parent
``tests/unit/integrations`` directory has none either, pytest's prepend
import mode would otherwise make this directory importable as a
top-level package named ``harbor``, shadowing the real Harbor
distribution and defeating ``pytest.importorskip("harbor")``. As a
consequence, test modules here import as top-level modules, so their
basenames must stay unique across all ``__init__``-less test dirs in
the repository.
"""

import os

assert not os.path.exists(
    os.path.join(os.path.dirname(__file__), "__init__.py")
), (
    "tests/unit/integrations/harbor must not contain an __init__.py — "
    "it would become importable as a top-level 'harbor' package and "
    "shadow the real Harbor distribution (see this conftest's "
    "docstring)."
)
