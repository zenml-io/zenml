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


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "scope: mark Secrets Manager tests that test scoping"
    )


def pytest_collection_modifyitems(config, items):
    flavor = config.getoption("secrets_manager_flavor")
    if flavor in ["local"]:
        # skip scope testing with secrets manager that don't understand scoping
        skip_scope = pytest.mark.skip(
            reason=f"{flavor} Secrets Manager Does not support scope"
        )
        for item in items:
            if "scope" in item.keywords:
                item.add_marker(skip_scope)
