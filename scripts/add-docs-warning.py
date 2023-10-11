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
"""Adds a warning to a version of ZenML Gitbook documentation."""

import os
import re


def get_version(version_file_path: str) -> str:
    """Get the ZenML version from the VERSION file.

    Args:
        version_file_path (str): Path to the VERSION file.

    Returns:
        str: The ZenML version.
    """
    with open(version_file_path, "r", encoding="utf-8") as vf:
        return vf.read().strip()


def process_files(root_dir: str, version: str) -> None:
    """Add the warning string to all markdown files.

    Args:
        root_dir (str): The root directory of the documentation.
        version (str): The ZenML version.
    """
    pattern = re.compile(r"---\ndescription: (?:.*| >-)\n---\n", re.DOTALL)
    warning_string = (
        '\n{% hint style="warning" %}\n'
        "This is an older version of the ZenML documentation. "
        "To read and view the latest version please "
        "[visit this up-to-date URL](https://docs.zenml.io).\n"
        "{% endhint %}\n\n"
    )

    for root, _, files in os.walk(root_dir):
        # Skip the drafts folder
        if "docs/book/drafts" in root:
            continue

        for file in files:
            # Skip toc.md
            if file == "toc.md":
                continue

            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Skip if warning string is already present
                if warning_string in content:
                    continue

                match = pattern.match(content)
                if match:
                    new_content = (
                        content[: match.end()]
                        + warning_string
                        + content[match.end() :]
                    )
                elif file in ["glossary.md", "usage-analytics.md"]:
                    new_content = warning_string + content
                else:
                    print(
                        f"Version {version}: Couldn't process file {file_path}"
                    )
                    continue  # Skip the rest of this iteration

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)


version = get_version("src/zenml/VERSION")
process_files("docs/book", version)
