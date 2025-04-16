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
from typing import Dict, List, Optional, Set, TextIO, Tuple

import yaml


def load_yaml_file(filepath: str) -> Dict:
    """Load a YAML file and return its contents as a dictionary.

    Args:
        filepath: The path to the YAML file

    Returns:
        A dictionary containing the YAML contents
    """
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def clean_header(header: str) -> str:
    """Clean up a header according to the specified rules.

    Args:
        header: The header to clean

    Returns:
        A cleaned header
    """
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

    The URL is constructed following these rules:
    - The current section header (## lines) is prepended to the URL
    - Indentation hierarchy is preserved in the URL structure
    - .md extensions are removed
    - README.md files convert to the parent directory name

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
    current_section = ""
    
    # Track hierarchy based on indentation
    hierarchy_stack = []
    prev_indent_level = 0

    for line in lines:
        line = line.rstrip()
        if not line:  # Skip empty lines
            continue

        # Check if this is a section header line (starting with ##)
        header_match = re.match(r"^##\s+(.+)$", line)
        if header_match:
            current_section = clean_header(header_match.group(1))
            # Reset hierarchy when encountering a new section
            hierarchy_stack = []
            prev_indent_level = 0
            continue

        # Check if this is a list item line with a link (* [something](somepath.md))
        list_match = re.match(r"^(\s*)(\*|\-)\s+\[([^\]]+)\]\(([^)]+)\)", line)
        if not list_match:
            continue

        # Extract indent level and filepath
        indentation = list_match.group(1)
        indent_level = len(indentation) // 2  # assuming 2 spaces per level
        item_title = list_match.group(3)
        item_path = list_match.group(4)

        # Handle hierarchy based on indentation
        if indent_level > prev_indent_level:
            # Going deeper, add previous item as part of the hierarchy
            if hierarchy_stack:
                # Don't add anything as we're just starting to indent
                pass
        elif indent_level < prev_indent_level:
            # Going back up, remove elements from the hierarchy
            levels_to_pop = prev_indent_level - indent_level
            for _ in range(min(levels_to_pop, len(hierarchy_stack))):
                hierarchy_stack.pop()

        # Process the item path
        path_parts = item_path.split("/")
        filename = path_parts[-1]
        
        # Handle the case where the file is a README.md
        if filename.lower() == "readme.md":
            if len(path_parts) > 1:
                # For README.md, use the parent directory name
                last_part = path_parts[-2]
                # Update hierarchy with the directory
                if indent_level == 0:
                    hierarchy_stack = [last_part]
                else:
                    # If we're already indented, add to hierarchy
                    if len(hierarchy_stack) == indent_level:
                        hierarchy_stack.append(last_part)
                    else:
                        hierarchy_stack = hierarchy_stack[:indent_level]
                        hierarchy_stack.append(last_part)
            else:
                # Root README.md, skip as there's no meaningful URL
                continue
        else:
            # For regular files, remove .md extension
            last_part = filename.replace(".md", "")
            
            # Update the hierarchy if needed
            if indent_level > 0:
                if len(hierarchy_stack) >= indent_level:
                    # We're at a level where we can just append
                    pass
                else:
                    # Missing hierarchy levels, reconstruct from path
                    for i in range(len(hierarchy_stack), indent_level):
                        if i < len(path_parts) - 1:
                            hierarchy_stack.append(path_parts[i])
                        else:
                            # Not enough parts in the path, use the title
                            hierarchy_stack.append(item_title.lower().replace(" ", "-"))
        
        # Construct the full URL
        if current_section:
            url_parts = [current_section]
            url_parts.extend(hierarchy_stack[:indent_level])
            if filename.lower() != "readme.md":
                url_parts.append(last_part)
        else:
            url_parts = []
            url_parts.extend(hierarchy_stack[:indent_level])
            if filename.lower() != "readme.md":
                url_parts.append(last_part)
        
        url = "/".join(url_parts)
        
        # Add this item to the stack for next iteration if it's at level 0
        if indent_level == 0:
            if filename.lower() == "readme.md":
                # Directory name already added above
                pass
            else:
                # Clear the hierarchy and start fresh with this item
                hierarchy_stack = []
        
        # Update prev_indent_level for the next iteration
        prev_indent_level = indent_level
        
        # Add to result
        result.append((url, item_path))

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
            target_path = os.path.normpath(
                os.path.join(root_path, redirect_target)
            )
        else:
            # Path already includes root or is absolute
            target_path = os.path.normpath(redirect_target)

        if target_path not in toc_filepaths:
            missing_files.append(target_path)

    return missing_files


def write_output(message: str, output_file: Optional[TextIO] = None):
    """Write output to both stdout and the output file if provided.

    Args:
        message: The message to output
        output_file: Optional file object to write to
    """
    print(message)
    if output_file:
        output_file.write(message + "\n")


def main():
    """Main function to run the GitBook checks."""
    parser = argparse.ArgumentParser(
        description="Check GitBook redirects for consistency"
    )
    parser.add_argument(
        "old_dir",
        help="Directory containing the base branch GitBook configuration",
    )
    parser.add_argument(
        "new_dir",
        help="Directory containing the PR branch GitBook configuration",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file to save results (optional)",
        type=str,
    )

    args = parser.parse_args()

    old_dir = args.old_dir
    new_dir = args.new_dir
    output_file_path = args.output

    # Open output file if specified
    output_file = None
    if output_file_path:
        output_file = open(output_file_path, "w")

    success = True
    total_missing_redirects = 0
    total_missing_files = 0

    try:
        # Load config files
        old_config = load_yaml_file(
            os.path.join(old_dir, "redirect-check.yaml")
        )
        new_config = load_yaml_file(
            os.path.join(new_dir, "redirect-check.yaml")
        )

        # Check for removed slugs
        removed_slugs = set(old_config.keys()) - set(new_config.keys())
        if removed_slugs:
            write_output(
                f"WARNING: The following slugs have been removed and need manual redirection in GitBook: {', '.join(removed_slugs)}",
                output_file,
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
            missing_files = check_toc_entries(
                redirects, new_filepaths, root_path
            )

            slug_has_errors = False

            # Report findings
            if missing_redirects:
                slug_has_errors = True
                success = False
                total_missing_redirects += len(missing_redirects)
                write_output(
                    f"ERROR in slug '{slug}': {len(missing_redirects)} URLs have been removed but are missing redirects:",
                    output_file,
                )
                for url in missing_redirects:
                    write_output(f"  - {url}", output_file)

            if missing_files:
                slug_has_errors = True
                success = False
                total_missing_files += len(missing_files)
                write_output(
                    f"ERROR in slug '{slug}': {len(missing_files)} redirect targets are missing from the TOC:",
                    output_file,
                )
                for filepath in missing_files:
                    write_output(f"  - {filepath}", output_file)

            if slug_has_errors:
                write_output("", output_file)  # Add empty line between slugs

        # Output the summary of all issues
        if total_missing_redirects > 0 or total_missing_files > 0:
            write_output("\nSUMMARY OF ISSUES:", output_file)
            write_output(
                f"Total missing redirects: {total_missing_redirects}",
                output_file,
            )
            write_output(
                f"Total missing files: {total_missing_files}", output_file
            )
            write_output(
                f"Total issues: {total_missing_redirects + total_missing_files}",
                output_file,
            )

        if success:
            write_output(
                "All GitBook redirect checks passed successfully!", output_file
            )

    finally:
        # Close output file if it was opened
        if output_file:
            output_file.close()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
    # parse_toc_file("/Users/bariscandurak/zenml/zenml/old/documentation/toc.md")