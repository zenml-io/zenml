#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from tests.unit.test_flavor import AriaOrchestratorFlavor


def test_docs_url_works(stub_component):
    """Tests that the docs url works."""
    from zenml import __version__

    aria_flavor = AriaOrchestratorFlavor()
    assert aria_flavor.docs_url is not None
    assert (
        aria_flavor.docs_url
        == f"https://apidocs.zenml.io/{__version__}/integration_code_docs/integrations-{aria_flavor.name}"
    )
