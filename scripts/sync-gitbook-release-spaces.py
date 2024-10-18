#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Syncs the Gitbook spaces accordingly for the new release."""

import os

import requests

# Constants
BASE_URL = "https://api.gitbook.com/v1"


def get_space_id(name, collection, organization, headers) -> str:
    # Make the initial list-spaces call
    params = {"limit": 50}

    response = requests.get(
        f"{BASE_URL}/orgs/{organization}/spaces",
        headers=headers,
        params=params,
    ).json()

    # Iterate through the pages until we can find the correct space
    while True:
        for space in response["items"]:
            if (
                space.get("parent", None) == collection
                and space.get("title", None) == name
            ):
                return space["id"]

        params.update(response["next"])
        response = requests.get(
            f"{BASE_URL}/orgs/{organization}/spaces",
            headers=headers,
            params=params,
        ).json()


def duplicate_space(space_id, headers):
    response = requests.post(
        f"{BASE_URL}/spaces/{space_id}/duplicate", headers=headers
    )
    if response.status_code != 200:
        raise requests.HTTPError("There was a problem duplicating the space.")
    return response.json()["id"]


def update_space(space_id, changes, headers):
    response = requests.patch(
        f"{BASE_URL}/spaces/{space_id}", headers=headers, json=changes
    )
    if response.status_code != 200:
        raise requests.HTTPError("There was a problem updating the space.")


def move_space(space_id, target_collection_id, headers):
    # Define the endpoint URL
    url = f"{BASE_URL}/spaces/{space_id}/move"

    # Create the payload for the request
    payload = {"parent": target_collection_id}

    # Make the POST request to move the space
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise requests.HTTPError("There was a problem moving the space.")


def main() -> None:
    # Get environment variables
    zenml_new_version = os.environ.get("ZENML_NEW_VERSION")
    zenml_old_version = os.environ.get("ZENML_VERSION")
    gitbook_api_key = os.environ.get("GITBOOK_API_KEY")
    gitbook_organization = os.environ.get("GITBOOK_ORGANIZATION")
    gitbook_docs_collection = os.environ.get("GITBOOK_DOCS_COLLECTION")
    gitbook_legacy_collection = os.environ.get("GITBOOK_LEGACY_COLLECTION")

    if not all(
        [
            zenml_new_version,
            zenml_old_version,
            gitbook_api_key,
            gitbook_organization,
            gitbook_docs_collection,
            gitbook_legacy_collection,
        ]
    ):
        raise EnvironmentError("Missing required environment variables")

    # Create the headers
    headers = {
        "Authorization": f"Bearer {gitbook_api_key}",
        "Content-Type": "application/json",
    }

    # 1. Get the Space ID of the previous release
    previous_release_space_id = get_space_id(
        name=zenml_old_version,
        collection=gitbook_docs_collection,
        organization=gitbook_organization,
        headers=headers,
    )

    # 2. Duplicate the previous release space
    new_release_space_id = duplicate_space(
        space_id=previous_release_space_id,
        headers=headers,
    )

    # 3: Rename the duplicate to the new name
    update_space(
        space_id=new_release_space_id,
        changes={"title": zenml_new_version},
        headers=headers,
    )

    # 4: Move the previous release to the legacy collection
    move_space(
        space_id=previous_release_space_id,
        target_collection_id=gitbook_legacy_collection,
        headers=headers,
    )


if __name__ == "__main__":
    main()
