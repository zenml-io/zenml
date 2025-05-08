#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

#!/usr/bin/env python3

import argparse
import os


def add_version_to_legacy_docs(version):
    """Add a new version to the legacy docs table.

    Args:
        version: The version number to add (e.g., '0.82.0')
    """
    url = (
        f"https://zenml-io.gitbook.io/zenml-legacy-documentation/v/{version}/"
    )

    # Path to the legacy docs file
    file_path = os.path.join("docs", "book", "reference", "legacy-docs.md")

    # Read the current file
    with open(file_path, "r") as f:
        content = f.read()

    # Find the start of the tbody section
    tbody_start = content.find("<tbody>") + len("<tbody>")

    # Create the new table row
    new_row = f'<tr><td>{version}</td><td></td><td></td><td><a href="{url}">{url}</a></td></tr>'

    # Insert the new row right after the tbody opening tag
    updated_content = content[:tbody_start] + new_row + content[tbody_start:]

    # Write the updated content back to the file
    with open(file_path, "w") as f:
        f.write(updated_content)

    print(f"✅ Added version {version} to legacy docs table")


def main():
    """Add a new version to the legacy docs table."""
    parser = argparse.ArgumentParser(
        description="Add a new version to the legacy docs table"
    )
    parser.add_argument(
        "version", help="The version number to add (e.g., 0.82.0)"
    )
    args = parser.parse_args()
    add_version_to_legacy_docs(args.version)


if __name__ == "__main__":
    main()
