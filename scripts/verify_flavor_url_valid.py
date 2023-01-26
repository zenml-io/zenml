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
"""Verify the current flavor implementations contains valid flavor_docs_urls.

Whenever new flavors are added or when the structure of the docs is adjusted,
there is potential to break the link between flavors and their corresponding
docs.

The `flavor_docs_url` property on flavors is built with a very specific
assumption of how this url is built. This script is designed to validate that
this assumption still holds. But there are some manual steps involved:

1) Push your code.

2) Use the GitBook UI to provision a Test Space with an unlisted public url
that uses your code.

3) Set the RootDomain of this unlisted gitbook space as FLAVOR_DOC_ROOT_DOMAIN

4) Run this script to make sure all the urls mentioned in code are working.
"""
from zenml.stack.flavor_registry import FlavorRegistry
import requests

FLAVOR_DOC_ROOT_DOMAIN = "https://zenml-io.gitbook.io/test-space"

flavor_registry = FlavorRegistry()

flavors = flavor_registry.builtin_flavors + flavor_registry.integration_flavors

for flavor in flavors:
    url_components = flavor().flavor_docs_url.split("/component-gallery", 1)
    url_components[0] = FLAVOR_DOC_ROOT_DOMAIN

    url = url_components[0] + "/component-gallery" + url_components[1]

    r = requests.head(url)
    if r.status_code == 404:
        print(f"{flavor().__class__}, flavor_docs_url points at {url} "
              f"which does not seem to exist.")
    else:
        print(f"{flavor().__class__} all good g.")
