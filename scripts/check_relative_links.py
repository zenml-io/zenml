#!/usr/bin/env python3
"""Script to verify that relative links in markdown files point to existing files in the repository.

This script scans markdown files for relative links and checks if they resolve to
actual files in the repository structure, without making any HTTP requests.

Usage:
    python check_relative_links.py --dir docs/book
"""

import argparse
import os
import re
import sys
from typing import List, Tuple


def find_markdown_files(directory: str) -> List[str]:
    """Find all markdown files in the given directory and its subdirectories."""
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    return markdown_files


def extract_relative_links(file_path: str) -> List[Tuple[str, int, str]]:
    """
    Extract all relative links from a markdown file along with line numbers.
    Returns list of tuples: (link, line_num, full_line)
    """
    links = []
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Regular expressions for different types of markdown links
    # Only match relative links that don't start with http/https/ftp/mailto
    inline_link_pattern = re.compile(
        r"\[(?:[^\]]+)\]\(((?!https?:|ftp:|mailto:)[^)]+)\)"
    )
    reference_link_def_pattern = re.compile(
        r"^\s*\[(?:[^\]]+)\]:\s*((?!https?:|ftp:|mailto:)\S+)"
    )
    html_link_pattern = re.compile(
        r'<a\s+(?:[^>]*?)href=["\']((?!https?:|ftp:|mailto:).*?)["\']',
        re.IGNORECASE,
    )

    for line_num, line in enumerate(lines, 1):
        # Find inline links [text](url)
        for match in inline_link_pattern.finditer(line):
            url = match.group(1).split()[0]  # Handle links with title
            links.append((url, line_num, line.strip()))

        # Find reference link definitions [id]: url
        for match in reference_link_def_pattern.finditer(line):
            url = match.group(1).split()[0]  # Handle links with title
            links.append((url, line_num, line.strip()))

        # Find HTML links <a href="url">
        for match in html_link_pattern.finditer(line):
            url = match.group(1).split()[0]  # Handle links with title
            links.append((url, line_num, line.strip()))

    return links


def resolve_relative_path(base_file: str, rel_path: str) -> str:
    """
    Resolve a relative path from a base file location.
    For instance, if base_file is 'docs/book/user-guide/a.md' and rel_path is '../b.md',
    this will return 'docs/book/b.md'.
    """
    # Handle fragment/anchor links (like file.md#section)
    fragment = ""
    if "#" in rel_path:
        rel_path, fragment = rel_path.split("#", 1)

    # Handle query parameters
    query = ""
    if "?" in rel_path:
        rel_path, query = rel_path.split("?", 1)

    # Get the directory of the base file
    base_dir = os.path.dirname(base_file)

    # Resolve the relative path
    resolved_path = os.path.normpath(os.path.join(base_dir, rel_path))

    # Return with original fragment and query
    result = resolved_path
    if fragment:
        result += f"#{fragment}"
    if query:
        result += f"?{query}"

    return result


def check_relative_links(dir_path: str) -> bool:
    """
    Check if all relative links in markdown files actually point to existing files.

    Returns True if all links are valid, False otherwise.
    """
    markdown_files = find_markdown_files(dir_path)
    print(
        f"Found {len(markdown_files)} markdown files in directory: {dir_path}"
    )

    broken_links = []
    valid_links_count = 0

    # Keep track of all checked links to avoid duplicates
    checked_links = set()

    # First, gather all markdown files for validating links
    all_md_files = set()
    for file_path in markdown_files:
        all_md_files.add(os.path.normpath(file_path))
        # Also add versions without .md extension
        if file_path.endswith(".md"):
            all_md_files.add(os.path.normpath(file_path[:-3]))

    # Also add README alternatives
    readme_alternatives = set()
    for file_path in all_md_files:
        if file_path.endswith("/README.md"):
            # Add directory path (without the README.md) as valid
            readme_alternatives.add(os.path.normpath(file_path[:-9]))
        elif file_path.endswith("/README"):
            readme_alternatives.add(os.path.normpath(file_path[:-7]))

    all_valid_paths = all_md_files.union(readme_alternatives)

    # Now check links
    for file_path in markdown_files:
        relative_links = extract_relative_links(file_path)
        file_broken_links = []

        for link, line_num, line in relative_links:
            # Skip links we've already checked
            link_check_key = f"{file_path}:{link}"
            if link_check_key in checked_links:
                continue

            checked_links.add(link_check_key)

            # Ignore links to assets, images, etc.
            if any(
                ignore in link
                for ignore in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".svg",
                    "assets",
                    ".gitbook",
                    "mailto:",
                ]
            ):
                continue

            # Resolve the relative link to a full path
            resolved_path = resolve_relative_path(file_path, link)

            # Strip fragments and queries for existence check
            check_path = resolved_path
            if "#" in check_path:
                check_path = check_path.split("#")[0]
            if "?" in check_path:
                check_path = check_path.split("?")[0]

            # Normalize the path
            check_path = os.path.normpath(check_path)

            # First check if file exists directly
            if os.path.exists(check_path):
                valid_links_count += 1
                continue

            # If it doesn't exist, try adding .md extension
            if not check_path.endswith(".md") and os.path.exists(
                f"{check_path}.md"
            ):
                valid_links_count += 1
                continue

            # If it's a directory, check if README.md exists
            if os.path.isdir(check_path) and os.path.exists(
                os.path.join(check_path, "README.md")
            ):
                valid_links_count += 1
                continue

            # Check against our pre-computed set of valid paths
            if check_path in all_valid_paths:
                valid_links_count += 1
                continue

            # If we get here, it's a broken link
            file_broken_links.append((link, line_num, resolved_path, line))

        # Print details about broken links in this file
        if file_broken_links:
            print(f"\n{file_path}:")
            for link, line_num, resolved_path, line in file_broken_links:
                print(f"  Line {line_num}: {link}")
                print(f"  Resolves to: {resolved_path}")
                print(f"  Context: {line}")
                broken_links.append((file_path, line_num, link, resolved_path))

    # Summary
    total_links = valid_links_count + len(broken_links)
    print(f"\nChecked {total_links} relative links:")
    print(f"  ✅ {valid_links_count} valid links")
    print(f"  ❌ {len(broken_links)} broken links")

    return len(broken_links) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Check if relative links in markdown files resolve to existing files"
    )
    parser.add_argument(
        "--dir", required=True, help="Directory to scan for links"
    )
    args = parser.parse_args()

    all_links_valid = check_relative_links(args.dir)

    if all_links_valid:
        print("\nAll relative links are valid!")
        return 0
    else:
        print(
            "\nFound broken relative links. Please fix them before proceeding."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
