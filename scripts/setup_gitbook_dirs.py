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
"""This script sets up the directory structure for GitBook redirect checks."""

import argparse
import os
import shutil
import sys

import yaml


def setup_directories(source_dir: str, output_dir: str) -> None:
    """Set up the directory structure for GitBook checks.

    Args:
        source_dir: Path to the source directory containing the repo
        output_dir: Path to the output directory to create the structure in
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Copy redirect-check.yaml
    redirect_check_path = os.path.join(
        source_dir, "docs/book/redirect-check.yaml"
    )
    if os.path.exists(redirect_check_path):
        shutil.copy(redirect_check_path, output_dir)
    else:
        print(f"ERROR: {redirect_check_path} does not exist")
        sys.exit(1)

    # Load the configuration
    with open(os.path.join(output_dir, "redirect-check.yaml"), "r") as f:
        config = yaml.safe_load(f)

    # Process each slug
    for slug, gitbook_path in config.items():
        # Create directory for the slug
        slug_dir = os.path.join(output_dir, slug)
        os.makedirs(slug_dir, exist_ok=True)

        # Construct full path to the gitbook.yaml file
        full_gitbook_path = os.path.join(source_dir, gitbook_path)

        if os.path.exists(full_gitbook_path):
            # Copy the gitbook.yaml file
            shutil.copy(
                full_gitbook_path, os.path.join(slug_dir, ".gitbook.yaml")
            )

            # Read the gitbook.yaml to find the TOC file
            with open(full_gitbook_path, "r") as gf:
                gitbook = yaml.safe_load(gf)

            if "structure" in gitbook and "summary" in gitbook["structure"]:
                toc_path = gitbook["structure"]["summary"]

                # Get the directory containing the gitbook.yaml file
                gitbook_dir = os.path.dirname(full_gitbook_path)

                # Get the root path (default to '.' if not specified)
                root_path = gitbook.get("root", ".")

                # If root is specified, it's relative to the gitbook.yaml location
                if root_path:
                    # Join the gitbook dir with the root path
                    base_path = os.path.normpath(
                        os.path.join(gitbook_dir, root_path)
                    )
                else:
                    base_path = gitbook_dir

                # Now join with the toc path to get the full path
                full_toc_path = os.path.normpath(
                    os.path.join(base_path, toc_path)
                )

                if os.path.exists(full_toc_path):
                    shutil.copy(
                        full_toc_path, os.path.join(slug_dir, "toc.md")
                    )
                else:
                    print(
                        f"ERROR: TOC file {full_toc_path} not found for slug {slug}"
                    )
                    sys.exit(1)
            else:
                print(
                    f"ERROR: No TOC file specified in gitbook.yaml for slug {slug}"
                )
                sys.exit(1)
        else:
            print(
                f"ERROR: GitBook file {full_gitbook_path} not found for slug {slug}"
            )
            sys.exit(1)


def main():
    """Main function to set up the directory structure for GitBook checks."""
    parser = argparse.ArgumentParser(
        description="Set up directory structure for GitBook checks"
    )
    parser.add_argument(
        "source_dir", help="Source directory containing the repository"
    )
    parser.add_argument(
        "output_dir", help="Output directory to create the structure in"
    )

    args = parser.parse_args()
    setup_directories(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()
