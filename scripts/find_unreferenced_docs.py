#!/usr/bin/env python3
"""
Script to find markdown files in the docs directory that are not referenced in any TOC file.
This helps identify "orphan" files that can potentially be removed.

Usage:
  python find_unreferenced_docs.py [--mode MODE] [--verbose] [--ignore-readmes] [--delete]

Options:
  --mode MODE    Output mode: 'default' (for deletion), 'readable' (for analysis with clickable links)
                 Default is 'default'
  --verbose      Show additional debug information about path resolution
  --ignore-readmes  Exclude README.md files from the results
  --delete       Delete the unreferenced files (USE WITH CAUTION!)

Output:
  - List of unreferenced markdown files grouped by directory
  - A flat list of all unreferenced files

Example:
  # To list unreferenced files in default format:
  python find_unreferenced_docs.py

  # To list unreferenced files in a readable format with clickable links:
  python find_unreferenced_docs.py --mode readable

  # To show debug information:
  python find_unreferenced_docs.py --verbose

  # To exclude README.md files from the results:
  python find_unreferenced_docs.py --ignore-readmes

  # To delete unreferenced files (USE WITH CAUTION!):
  python find_unreferenced_docs.py --delete

  # To delete unreferenced files except README.md files:
  python find_unreferenced_docs.py --delete --ignore-readmes
"""

import argparse
import glob
import os
import re
import textwrap
from collections import defaultdict

# Base directory for docs
DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs/book"
)
TOC_FILES = [
    os.path.join(DOCS_DIR, "toc.md"),
    os.path.join(DOCS_DIR, "component-guide", "toc.md"),
    os.path.join(DOCS_DIR, "api-docs", "toc.md"),
    os.path.join(DOCS_DIR, "sdk-docs", "toc.md"),
    os.path.join(DOCS_DIR, "getting-started", "zenml-pro", "toc.md"),
    os.path.join(DOCS_DIR, "user-guide", "toc.md"),
]

# Global debug flag
verbose = False


def debug_print(*args, **kwargs):
    """Print only if verbose mode is enabled."""
    if verbose:
        print(*args, **kwargs)


def parse_toc_links(toc_file):
    """Extract all markdown file links from a TOC file."""
    if not os.path.exists(toc_file):
        print(f"WARNING: TOC file not found: {toc_file}")
        return []

    with open(toc_file, "r") as f:
        content = f.read()

    # Regular expression to find markdown links
    # This pattern finds: [link text](path/to/file.md)
    pattern = r"\[.*?\]\((.*?\.md)\)"
    links = re.findall(pattern, content)

    debug_print(f"\nProcessing TOC file: {toc_file}")
    debug_print(f"Found {len(links)} links in the TOC file")

    # Get the directory of the TOC file to resolve relative paths
    toc_dir = os.path.dirname(toc_file)

    # Resolve relative paths
    resolved_links = []
    for link in links:
        # Skip external links or anchors
        if link.startswith(("http://", "https://", "#")):
            debug_print(f"  Skipping external link: {link}")
            continue

        original_link = link

        # Handle relative paths
        if not link.startswith("/"):
            # This is a fix for the path resolution issue
            # We need to join the TOC directory with the relative path
            link = os.path.normpath(os.path.join(toc_dir, link))

        # Ensure the link is absolute - this is critical for proper matching
        if not os.path.isabs(link):
            link = os.path.abspath(link)

        debug_print(f"  Resolved: {original_link} -> {link}")
        resolved_links.append(link)

    return resolved_links


def find_all_md_files():
    """Find all markdown files in the docs directory."""
    files = glob.glob(os.path.join(DOCS_DIR, "**", "*.md"), recursive=True)
    # Convert to absolute paths for consistent comparison
    abs_files = [os.path.abspath(f) for f in files]

    debug_print(
        f"Found {len(abs_files)} total markdown files in the docs directory"
    )
    return abs_files


def filter_readmes(files):
    """Filter out README.md files from the list."""
    return [f for f in files if os.path.basename(f).lower() != "readme.md"]


def group_by_directory(files):
    """Group files by their parent directory."""
    groups = defaultdict(list)
    for file in files:
        # Get the parent directory
        parent_dir = os.path.dirname(file)
        groups[parent_dir].append(file)

    return groups


def format_file_list(files, width=80):
    """Format a list of files with line wrapping to improve readability."""
    # Convert absolute paths to relative paths from workspace root
    rel_files = [
        os.path.relpath(f, os.path.dirname(DOCS_DIR)) for f in sorted(files)
    ]

    # Join with spaces and wrap to fit the terminal width
    text = " ".join(rel_files)
    wrapped_text = textwrap.fill(text, width=width)

    return wrapped_text


def delete_files(files):
    """Delete the specified files."""
    deleted_count = 0
    failed_count = 0

    for file in files:
        try:
            os.remove(file)
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {file}: {str(e)}")
            failed_count += 1

    return deleted_count, failed_count


def print_default_format(unreferenced_files, grouped_files):
    """Print in the default format optimized for deletion."""
    print(f"Found {len(unreferenced_files)} unreferenced markdown files:")
    print("\n# Unreferenced Markdown Files")
    print("# Format: One directory group per line, files separated by spaces")
    print("\n# --------------- GROUPED BY DIRECTORY ---------------")

    for directory, files in sorted(grouped_files.items()):
        rel_dir = os.path.relpath(directory, os.path.dirname(DOCS_DIR))
        print(f"\n# {rel_dir}/")
        print(format_file_list(files))

    print("\n# --------------- FLAT LIST ---------------")
    # Also print a flat list
    print("# Full list of unreferenced files:")
    print(format_file_list(unreferenced_files))


def print_readable_format(unreferenced_files, grouped_files):
    """Print in a readable format with clickable links for analysis."""
    workspace_dir = os.path.dirname(DOCS_DIR)

    # Calculate stats for summary
    total_files = len(unreferenced_files)
    total_directories = len(grouped_files)

    # Terminal width
    term_width = 100

    # Print header
    print("╔" + "═" * (term_width - 2) + "╗")
    print("║ 🔍  UNREFERENCED FILES REPORT" + " " * (term_width - 31) + "║")
    print("╚" + "═" * (term_width - 2) + "╝")
    print()

    # Print summary section
    print("┌" + "─" * (term_width - 2) + "┐")
    print("│ 📊  SUMMARY" + " " * (term_width - 13) + "│")
    print("├" + "─" * (term_width - 2) + "┤")
    print(
        f"│  • Total unreferenced files: {total_files}"
        + " " * (term_width - 35 - len(str(total_files)))
        + "│"
    )
    print(
        f"│  • Directories with unreferenced files: {total_directories}"
        + " " * (term_width - 47 - len(str(total_directories)))
        + "│"
    )
    print("└" + "─" * (term_width - 2) + "┘")
    print()

    # Print directories summary
    print("┌" + "─" * (term_width - 2) + "┐")
    print("│ 📁  DIRECTORIES BY FILE COUNT" + " " * (term_width - 30) + "│")
    print("├" + "─" * (term_width - 2) + "┤")

    # Sort directories by file count
    sorted_dirs = sorted(
        grouped_files.items(), key=lambda x: len(x[1]), reverse=True
    )

    # Print directory summary
    for directory, files in sorted_dirs:
        rel_dir = os.path.relpath(directory, workspace_dir)
        # Truncate long directory names
        if len(rel_dir) > term_width - 20:
            display_dir = rel_dir[: term_width - 23] + "..."
        else:
            display_dir = rel_dir

        count_str = f"[{len(files)} files]"
        padding = term_width - len(display_dir) - len(count_str) - 5
        print(f"│  {display_dir}" + " " * padding + f"{count_str} │")

    print("└" + "─" * (term_width - 2) + "┘")
    print()

    # Print detailed file listing
    print("┌" + "─" * (term_width - 2) + "┐")
    print("│ 📋  DETAILED FILE LISTING" + " " * (term_width - 25) + "│")
    print("└" + "─" * (term_width - 2) + "┘")

    # Print files grouped by directory
    for directory, files in sorted_dirs:
        rel_dir = os.path.relpath(directory, workspace_dir)

        # Print directory header
        print()
        print(f"📂  {rel_dir}/  [{len(files)} files]")
        print("─" * term_width)

        # Print files
        for i, file in enumerate(sorted(files), 1):
            # Get filename without directory path
            filename = os.path.basename(file)
            abs_file_path = os.path.abspath(file)

            # Create a clickable link (file:// protocol)
            clickable_link = f"file://{abs_file_path}"

            # Print file with its clickable link
            print(f"  {i:2d}. {filename}")
            print(f"      👉 {clickable_link}")

        # Add a separator between directories
        if i < len(sorted_dirs):
            print()

    # Don't print a deletion command since we have a --delete flag now
    print()


def main():
    global verbose

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Find markdown files not referenced in any TOC file."
    )
    parser.add_argument(
        "--mode",
        choices=["default", "readable"],
        default="default",
        help="Output mode: 'default' (for deletion) or 'readable' (for analysis with clickable links)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show additional debug information about path resolution",
    )
    parser.add_argument(
        "--ignore-readmes",
        action="store_true",
        help="Exclude README.md files from the results",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the unreferenced files (USE WITH CAUTION!)",
    )
    args = parser.parse_args()

    # Set the global verbose flag
    verbose = args.verbose

    # Check if all TOC files exist
    for toc_file in TOC_FILES:
        if not os.path.exists(toc_file):
            print(f"WARNING: TOC file not found: {toc_file}")

    # Parse all TOC files to get referenced files
    referenced_files = set()
    for toc_file in TOC_FILES:
        links = parse_toc_links(toc_file)
        referenced_files.update(links)

    debug_print(f"\nTotal referenced files found: {len(referenced_files)}")

    # Find all markdown files
    all_md_files = set(find_all_md_files())

    # Find unreferenced files
    unreferenced_files = all_md_files - referenced_files

    # Remove TOC files from the unreferenced list
    toc_files = set([os.path.abspath(toc) for toc in TOC_FILES])
    unreferenced_files = unreferenced_files - toc_files

    # Filter README.md files if requested
    if args.ignore_readmes:
        readme_count = sum(
            1
            for f in unreferenced_files
            if os.path.basename(f).lower() == "readme.md"
        )
        debug_print(f"Filtering out {readme_count} README.md files")
        unreferenced_files = set(filter_readmes(unreferenced_files))

    # Group unreferenced files by directory
    grouped_files = group_by_directory(unreferenced_files)

    # Handle deletion if requested
    if args.delete:
        if not unreferenced_files:
            print("No unreferenced files to delete.")
            return

        total_files = len(unreferenced_files)
        confirm = input(
            f"⚠️  WARNING: This will delete {total_files} files. Type 'YES' to confirm: "
        )

        if confirm.strip() == "YES":
            deleted_count, failed_count = delete_files(unreferenced_files)

            print(f"\n✅ Deleted {deleted_count} files successfully.")
            if failed_count > 0:
                print(f"❌ Failed to delete {failed_count} files.")
        else:
            print("\n❌ Deletion cancelled.")
        return

    # Print the results in the chosen format
    if args.mode == "readable":
        print_readable_format(unreferenced_files, grouped_files)
    else:  # default mode
        print_default_format(unreferenced_files, grouped_files)


if __name__ == "__main__":
    main()
