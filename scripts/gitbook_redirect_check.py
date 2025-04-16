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
"""This script checks the GitBook configuration for a given slug.

It checks:
- if all URLs that exist in the old TOC but not in the new one are
 present in the redirects section of the new GitBook YAML.
- if all redirect targets exist in the TOC.
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Set, Tuple

import yaml


def load_yaml_file(filepath: str) -> Dict:
    """Load a YAML file and return its contents as a dictionary."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def clean_header(header: str) -> str:
    """Clean up a header according to the specified rules."""
    # Strip HTML tags like <a href="#tutorial" id="tutorial"></a>
    header = re.sub(r"<[^>]+>", "", header).strip()

    # Convert to lowercase
    header = header.lower()

    # Replace '&' with 'and'
    header = header.replace("&", "and")

    # Replace spaces with hyphens
    header = header.replace(" ", "-")

    # Remove any special characters and clean up multiple hyphens
    header = re.sub(r"[^a-z0-9-]", "", header)
    header = re.sub(r"-+", "-", header)

    return header


def parse_toc_file(filepath: str) -> List[Tuple[str, str]]:
    """Parse a TOC markdown file and return a list of (url, filepath) tuples.

    The URL is constructed according to the rules:
        - Header is included if present
        - Spaces at the beginning determine the nesting level
        - Extensions are removed
        - README.md is treated specially

    Args:
        filepath: The path to the TOC markdown file

    Returns:
        A list of (url, filepath) tuples
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r") as f:
        lines = f.readlines()

    result = []
    current_header = ""
    prefix_stack = []
    current_prefix = ""

    for line in lines:
        line = line.rstrip()
        if not line:  # Skip empty lines
            continue

        # Check if this is a header line
        header_match = re.match(r"^##\s+(.+)$", line)
        if header_match:
            current_header = clean_header(header_match.group(1))
            prefix_stack = []
            current_prefix = ""
            continue

        # Check if this is a list item line
        list_match = re.match(r"^(\s*)(\*|\-)\s+\[([^\]]+)\]\(([^)]+)\)", line)
        if not list_match:
            continue

        spaces = list_match.group(1)
        filepath = list_match.group(4)

        # Count spaces to determine nesting level
        space_count = len(spaces)

        # Determine the current prefix based on nesting level
        if not prefix_stack:
            # First item at this level
            prefix_stack.append("")
            current_prefix = ""
        elif space_count > len(prefix_stack[-1]):
            # Going deeper
            last_part = (
                prefix_stack[-1].split("/")[-1] if prefix_stack[-1] else ""
            )
            prefix_stack.append(
                f"{prefix_stack[-1]}/{last_part}"
                if last_part
                else prefix_stack[-1]
            )
            current_prefix = prefix_stack[-1]
        elif space_count < len(prefix_stack[-1]):
            # Going back up
            while prefix_stack and len(prefix_stack[-1]) > space_count:
                prefix_stack.pop()
            current_prefix = prefix_stack[-1] if prefix_stack else ""

        # Parse the filepath
        path_parts = filepath.split("/")
        filename = path_parts[-1]

        # Generate URL part from the filename
        if filename.lower() == "readme.md":
            # Special handling for README.md
            if len(path_parts) > 1:
                url_part = path_parts[-2].lower()
            else:
                url_part = ""
        else:
            # Remove .md extension
            url_part = filename.lower().replace(".md", "")

        # Construct the full URL
        url = f"{current_header}/{current_prefix}/{url_part}".strip("/")

        # Normalize multiple slashes
        url = re.sub(r"/+", "/", url)

        # Add to result
        result.append((url, filepath))

    return result


def check_redirects(old_urls: Set[str], new_gitbook_yaml: Dict) -> List[str]:
    """Check if all URLs that exist in the old TOC but not in the new one.

    Args:
        old_urls: A set of URLs that exist in the old TOC
        new_gitbook_yaml: The new GitBook YAML

    Returns:
        A list of missing redirects
    """
    missing_redirects = []
    redirects = new_gitbook_yaml.get("redirects", {})

    for old_url in old_urls:
        found = False
        for redirect_src in redirects:
            if redirect_src == old_url or redirect_src.endswith(f"/{old_url}"):
                found = True
                break

        if not found:
            missing_redirects.append(old_url)

    return missing_redirects


def check_toc_entries(
    redirects: Dict[str, str], toc_filepaths: Set[str], root_path: str
) -> List[str]:
    """Check if all redirect targets exist in the TOC.

    Args:
        redirects: A dictionary of redirects
        toc_filepaths: A set of filepaths in the TOC
        root_path: The root path of the GitBook

    Returns:
        A list of missing filepaths
    """
    missing_files = []

    for redirect_target in redirects.values():
        # Handle paths correctly using the root path from gitbook.yaml
        # Note: This assumes the toc_filepaths are in the same format as the redirects
        # i.e., both are relative to the same base or both contain the same prefixes
        if root_path and not redirect_target.startswith(root_path):
            # Path is relative to the root path
            target_path = os.path.normpath(os.path.join(root_path, redirect_target))
        else:
            # Path already includes root or is absolute
            target_path = os.path.normpath(redirect_target)

        if target_path not in toc_filepaths:
            missing_files.append(target_path)

    return missing_files


def main():
    """Main function to run the GitBook checks."""
    parser = argparse.ArgumentParser(
        description="Check GitBook redirects for consistency"
    )
    parser.add_argument(
        "old_dir", help="Directory containing the base branch GitBook configuration"
    )
    parser.add_argument(
        "new_dir", help="Directory containing the PR branch GitBook configuration"
    )
    
    args = parser.parse_args()
    
    old_dir = args.old_dir
    new_dir = args.new_dir

    # Load config files
    old_config = load_yaml_file(os.path.join(old_dir, "redirect-check.yaml"))
    new_config = load_yaml_file(os.path.join(new_dir, "redirect-check.yaml"))

    # Check for removed slugs
    removed_slugs = set(old_config.keys()) - set(new_config.keys())
    if removed_slugs:
        print(
            f"WARNING: The following slugs have been removed and need manual redirection in GitBook: {', '.join(removed_slugs)}"
        )

    # Process each slug that exists in both old and new
    common_slugs = set(old_config.keys()) & set(new_config.keys())
    for slug in common_slugs:
        old_toc_path = os.path.join(old_dir, slug, "toc.md")
        new_toc_path = os.path.join(new_dir, slug, "toc.md")
        new_gitbook_path = os.path.join(new_dir, slug, ".gitbook.yaml")

        # Parse TOC files
        old_toc_entries = parse_toc_file(old_toc_path)
        new_toc_entries = parse_toc_file(new_toc_path)

        # Extract URLs and filepaths
        old_urls = {url for url, _ in old_toc_entries}
        new_urls = {url for url, _ in new_toc_entries}
        new_filepaths = {filepath for _, filepath in new_toc_entries}

        # Load the new GitBook YAML
        new_gitbook_yaml = load_yaml_file(new_gitbook_path)
        root_path = new_gitbook_yaml.get("root", "")

        # Check 1: Find URLs that exist in old but not in new, and ensure they're in redirects
        removed_urls = old_urls - new_urls
        missing_redirects = check_redirects(removed_urls, new_gitbook_yaml)

        # Check 2: Ensure all redirect targets exist in the TOC
        redirects = new_gitbook_yaml.get("redirects", {})
        missing_files = check_toc_entries(redirects, new_filepaths, root_path)

        # Report findings
        if missing_redirects:
            print(
                f"ERROR in slug '{slug}': The following URLs have been removed but are missing redirects:"
            )
            for url in missing_redirects:
                print(f"  - {url}")
            sys.exit(1)

        if missing_files:
            print(
                f"ERROR in slug '{slug}': The following redirect targets are missing from the TOC:"
            )
            for filepath in missing_files:
                print(f"  - {filepath}")
            sys.exit(1)

    print("All GitBook redirect checks passed successfully!")


if __name__ == "__main__":
    main()
