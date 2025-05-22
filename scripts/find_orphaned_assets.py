#!/usr/bin/env python3
"""
Script to find image assets in all .gitbook/assets directories that are not referenced in any markdown file.
This helps identify "orphan" assets that can potentially be removed.

Usage:
  python find_orphaned_assets.py [--mode MODE] [--verbose] [--delete]

Options:
  --mode MODE    Output mode: 'default' (for deletion), 'readable' (for analysis with clickable links)
                 Default is 'default'
  --verbose      Show additional debug information about path resolution
  --delete       Delete the orphaned assets (USE WITH CAUTION!)

Output:
  - List of orphaned image files
  - Stats about referenced vs. orphaned assets
  - Total space that would be saved by deletion

Example:
  # To list orphaned assets in default format:
  python find_orphaned_assets.py

  # To list orphaned assets in a readable format with clickable links:
  python find_orphaned_assets.py --mode readable

  # To show debug information:
  python find_orphaned_assets.py --verbose

  # To delete orphaned assets (USE WITH CAUTION!):
  python find_orphaned_assets.py --delete
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

# Image file extensions to look for
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]

# Global debug flag
verbose = False


def debug_print(*args, **kwargs):
    """Print only if verbose mode is enabled."""
    if verbose:
        print(*args, **kwargs)


def find_all_assets_dirs():
    """Find all .gitbook/assets directories in the docs structure."""
    # Look for .gitbook/assets directories
    pattern = os.path.join(DOCS_DIR, "**", ".gitbook", "assets")
    assets_dirs = glob.glob(pattern, recursive=True)

    # Add the main assets directory if it's not already included
    main_assets_dir = os.path.join(DOCS_DIR, ".gitbook", "assets")
    if os.path.exists(main_assets_dir) and main_assets_dir not in assets_dirs:
        assets_dirs.append(main_assets_dir)

    debug_print(f"Found {len(assets_dirs)} .gitbook/assets directories:")
    for assets_dir in assets_dirs:
        debug_print(f"  - {os.path.relpath(assets_dir, DOCS_DIR)}")

    return assets_dirs


def find_all_md_files():
    """Find all markdown files in the docs directory."""
    files = glob.glob(os.path.join(DOCS_DIR, "**", "*.md"), recursive=True)
    # Convert to absolute paths for consistent comparison
    abs_files = [os.path.abspath(f) for f in files]

    debug_print(
        f"Found {len(abs_files)} total markdown files in the docs directory"
    )
    return abs_files


def find_all_assets():
    """Find all image assets in all .gitbook/assets directories."""
    all_assets = []
    assets_dirs = find_all_assets_dirs()

    for assets_dir in assets_dirs:
        assets_in_dir = 0
        for ext in IMAGE_EXTENSIONS:
            pattern = os.path.join(assets_dir, f"**/*{ext}")
            assets = glob.glob(pattern, recursive=True)
            all_assets.extend(assets)
            assets_in_dir += len(assets)

        debug_print(
            f"Found {assets_in_dir} assets in {os.path.relpath(assets_dir, DOCS_DIR)}"
        )

    # Convert to absolute paths for consistent comparison
    abs_assets = [os.path.abspath(f) for f in all_assets]

    debug_print(
        f"Found {len(abs_assets)} total image assets across all .gitbook/assets directories"
    )
    return abs_assets


def extract_asset_references(md_file):
    """Extract all image asset references from a markdown file."""
    with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Pattern for markdown image references: ![alt text](path/to/image.ext)
    md_pattern = (
        r"!\[.*?\]\((.*?(?:\.jpg|\.jpeg|\.png|\.gif|\.svg|\.webp).*?)\)"
    )

    # Pattern for HTML image references: <img src="path/to/image.ext" ...>
    html_pattern = r'<img[^>]*src=["\']([^"\']*(?:\.jpg|\.jpeg|\.png|\.gif|\.svg|\.webp)[^"\']*)["\'][^>]*>'

    # Pattern for GitBook card references: <a href=".gitbook/assets/image.ext">image.ext</a>
    gitbook_pattern = r'<a[^>]*href=["\']([^"\']*(?:\.jpg|\.jpeg|\.png|\.gif|\.svg|\.webp)[^"\']*)["\'][^>]*>'

    # Additional pattern for CSS background images
    css_pattern = r'url\([\'"]?([^\'")]*(?:\.jpg|\.jpeg|\.png|\.gif|\.svg|\.webp)[^\'")]*)[\'"]?\)'

    # Combine all patterns
    references = []
    references.extend(re.findall(md_pattern, content))
    references.extend(re.findall(html_pattern, content))
    references.extend(re.findall(gitbook_pattern, content))
    references.extend(re.findall(css_pattern, content))

    debug_print(f"Processing markdown file: {md_file}")
    debug_print(f"Found {len(references)} image references")

    # Resolve relative paths
    resolved_refs = []
    for ref in references:
        # Skip external links
        if ref.startswith(("http://", "https://", "data:")):
            debug_print(f"  Skipping external link: {ref}")
            continue

        original_ref = ref

        # Normalize the path (handle relative paths)
        if ref.startswith(".gitbook/assets/"):
            # Convert to absolute path using the markdown file's directory
            md_dir = os.path.dirname(md_file)
            ref = os.path.normpath(os.path.join(md_dir, ref))
        elif ref.startswith("../"):
            # Relative to the markdown file's directory
            md_dir = os.path.dirname(md_file)
            ref = os.path.normpath(os.path.join(md_dir, ref))
        elif not ref.startswith("/") and not os.path.isabs(ref):
            # Relative to the markdown file's directory
            md_dir = os.path.dirname(md_file)
            ref = os.path.normpath(os.path.join(md_dir, ref))

        # Ensure the reference is absolute for consistent comparison
        if not os.path.isabs(ref):
            ref = os.path.abspath(ref)

        debug_print(f"  Resolved: {original_ref} -> {ref}")
        resolved_refs.append(ref)

    return resolved_refs


def get_human_readable_size(size_bytes):
    """Convert bytes to a human-readable format (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0 or unit == "GB":
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} {unit}"


def calculate_total_size(files):
    """Calculate the total size of all files in bytes."""
    total_size = 0
    for file in files:
        try:
            total_size += os.path.getsize(file)
        except (FileNotFoundError, PermissionError) as e:
            debug_print(f"Error getting size of {file}: {str(e)}")
    return total_size


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
    deleted_size = 0

    for file in files:
        try:
            file_size = os.path.getsize(file)
            os.remove(file)
            deleted_count += 1
            deleted_size += file_size
        except Exception as e:
            print(f"Error deleting {file}: {str(e)}")
            failed_count += 1

    return deleted_count, failed_count, deleted_size


def print_default_format(orphaned_assets, total_assets):
    """Print in the default format optimized for deletion."""
    total_size = calculate_total_size(orphaned_assets)
    human_readable_size = get_human_readable_size(total_size)

    print(
        f"Found {len(orphaned_assets)} orphaned assets out of {total_assets} total assets:"
    )
    print(f"Total space that would be saved: {human_readable_size}")
    print("\n# Orphaned Assets")
    print("# Format: Files separated by spaces")
    print("\n# --------------- ORPHANED ASSETS LIST ---------------")
    print(format_file_list(orphaned_assets))


def print_readable_format(orphaned_assets, total_assets):
    """Print in a readable format with clickable links for analysis."""
    # Calculate stats
    orphaned_count = len(orphaned_assets)
    referenced_count = total_assets - orphaned_count
    orphaned_percentage = (
        (orphaned_count / total_assets) * 100 if total_assets > 0 else 0
    )

    # Calculate total size
    orphaned_size = calculate_total_size(orphaned_assets)
    human_readable_size = get_human_readable_size(orphaned_size)

    # Terminal width
    term_width = 100

    # Print header
    print("╔" + "═" * (term_width - 2) + "╗")
    print("║ 🔍  ORPHANED ASSETS REPORT" + " " * (term_width - 29) + "║")
    print("╚" + "═" * (term_width - 2) + "╝")
    print()

    # Print summary section
    print("┌" + "─" * (term_width - 2) + "┐")
    print("│ 📊  SUMMARY" + " " * (term_width - 13) + "│")
    print("├" + "─" * (term_width - 2) + "┤")
    print(
        f"│  • Total assets: {total_assets}"
        + " " * (term_width - 19 - len(str(total_assets)))
        + "│"
    )
    print(
        f"│  • Referenced assets: {referenced_count} ({100 - orphaned_percentage:.1f}%)"
        + " " * (term_width - 36 - len(str(referenced_count)) - 7)
        + "│"
    )
    print(
        f"│  • Orphaned assets: {orphaned_count} ({orphaned_percentage:.1f}%)"
        + " " * (term_width - 33 - len(str(orphaned_count)) - 7)
        + "│"
    )
    print(
        f"│  • Total space that would be saved: {human_readable_size}"
        + " " * (term_width - 38 - len(human_readable_size))
        + "│"
    )
    print("└" + "─" * (term_width - 2) + "┘")
    print()

    # Group orphaned assets by their .gitbook/assets directory
    by_assets_dir = defaultdict(list)
    sizes_by_dir = defaultdict(int)

    for asset in orphaned_assets:
        # Find the .gitbook/assets part of the path
        path_parts = asset.split(os.path.sep)
        for i in range(len(path_parts)):
            if (
                i > 0
                and path_parts[i - 1] == ".gitbook"
                and path_parts[i] == "assets"
            ):
                # Get the parent directory of the .gitbook folder
                parent_dir = os.path.sep.join(path_parts[: i - 1])
                by_assets_dir[parent_dir].append(asset)
                sizes_by_dir[parent_dir] += os.path.getsize(asset)
                break

    # Print assets grouped by .gitbook/assets directory
    print("┌" + "─" * (term_width - 2) + "┐")
    print("│ 📋  ORPHANED ASSETS BY DIRECTORY" + " " * (term_width - 32) + "│")
    print("└" + "─" * (term_width - 2) + "┘")
    print()

    for assets_dir, files in sorted(by_assets_dir.items()):
        rel_dir = (
            os.path.relpath(assets_dir, DOCS_DIR)
            if assets_dir.startswith(DOCS_DIR)
            else assets_dir
        )
        dir_size = get_human_readable_size(sizes_by_dir[assets_dir])
        print(
            f"📁  {rel_dir}/.gitbook/assets/ ({len(files)} files, {dir_size})"
        )
        print("─" * term_width)

        # Group by extension within each directory
        by_ext = defaultdict(list)
        sizes_by_ext = defaultdict(int)

        for asset in files:
            ext = os.path.splitext(asset)[1].lower()
            by_ext[ext].append(asset)
            sizes_by_ext[ext] += os.path.getsize(asset)

        for ext, ext_files in sorted(by_ext.items()):
            ext_size = get_human_readable_size(sizes_by_ext[ext])
            print(f"  {ext} files ({len(ext_files)}, {ext_size})")

            for i, file in enumerate(sorted(ext_files), 1):
                filename = os.path.basename(file)
                abs_file_path = os.path.abspath(file)
                file_size = os.path.getsize(file) / 1024  # Size in KB

                # Create a clickable link
                clickable_link = f"file://{abs_file_path}"

                # Print file with its clickable link and size
                print(f"    {i:2d}. {filename} ({file_size:.1f} KB)")
                print(f"        👉 {clickable_link}")

            print()  # Extra line between extensions

        print()  # Extra line between directories


def main():
    global verbose

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Find image assets not referenced in any markdown file."
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
        "--delete",
        action="store_true",
        help="Delete the orphaned assets (USE WITH CAUTION!)",
    )
    args = parser.parse_args()

    # Set the global verbose flag
    verbose = args.verbose

    # Find all assets
    all_assets = find_all_assets()
    total_assets = len(all_assets)

    if total_assets == 0:
        print("No assets found in any .gitbook/assets directory.")
        return

    # Find all markdown files
    md_files = find_all_md_files()

    # Collect all referenced assets
    referenced_assets = set()
    for md_file in md_files:
        refs = extract_asset_references(md_file)
        referenced_assets.update(refs)

    debug_print(f"\nTotal referenced assets found: {len(referenced_assets)}")

    # Find orphaned assets
    orphaned_assets = set(all_assets) - referenced_assets

    # Handle deletion if requested
    if args.delete:
        if not orphaned_assets:
            print("No orphaned assets to delete.")
            return

        total_files = len(orphaned_assets)
        total_size = calculate_total_size(orphaned_assets)
        human_readable_size = get_human_readable_size(total_size)

        confirm = input(
            f"⚠️ WARNING: This will delete {total_files} image assets ({human_readable_size}). Type 'YES' to confirm: "
        )

        if confirm.strip() == "YES":
            deleted_count, failed_count, deleted_size = delete_files(
                orphaned_assets
            )
            deleted_size_str = get_human_readable_size(deleted_size)

            print(
                f"\n✅ Deleted {deleted_count} assets successfully, freeing up {deleted_size_str}."
            )
            if failed_count > 0:
                print(f"❌ Failed to delete {failed_count} assets.")
        else:
            print("\n❌ Deletion cancelled.")
        return

    # Print the results in the chosen format
    if args.mode == "readable":
        print_readable_format(orphaned_assets, total_assets)
    else:  # default mode
        print_default_format(orphaned_assets, total_assets)


if __name__ == "__main__":
    main()
