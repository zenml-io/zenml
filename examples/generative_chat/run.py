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
import logging

from pipelines.indices_builder import (
    build_indices_for_zenml_versions,
)


def main():
    print("Fetching zenml versions...")
    # versions = get_zenml_versions()  # all release versions
    versions = ["0.10.0", "0.35.1"]

    print(f"Found {len(versions)} versions.")
    print("Building indices for zenml versions...")
    build_indices_for_zenml_versions(versions)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main()
