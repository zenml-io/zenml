#!/usr/bin/env python3
"""Link Checker Script.

This script is a comprehensive tool for managing and validating links in ZenML's documentation.
It provides several key features:

1. Link Detection:
   - Scans markdown files for various types of links (inline, reference-style, HTML, and bare URLs)
   - Can search for links containing specific substrings
   - Supports both directory-wide and file-specific scanning

2. Link Transformation:
   - Converts relative documentation links to absolute URLs
   - Handles various link formats including README.md files
   - Preserves fragments and query parameters
   - Supports custom URL path mappings for specific directories or path segments

3. Link Validation:
   - Validates links by making HTTP requests
   - Supports parallel validation for better performance
   - Provides detailed error reporting for broken links

Usage Examples:
    # Find all links containing 'docs.zenml.io' in a directory
    python link_checker.py --dir docs/book --substring docs.zenml.io

    # Check specific files for links containing 'how-to'
    python link_checker.py --files file1.md file2.md --substring how-to

    # Preview link replacements without making changes
    python link_checker.py --files file1.md --replace-links --dry-run

    # Replace and validate links
    python link_checker.py --files file1.md --replace-links --validate-links

    # Customize HTTP request timeout
    python link_checker.py --files file1.md --validate-links --timeout 15

    # Use custom URL path mappings
    python link_checker.py --dir docs --replace-links --url-mapping user-guide=user-guides

Arguments:
    --dir: Directory containing markdown files to scan
    --files: List of specific markdown files to scan
    --substring: Substring to search for in links
    --replace-links: Replace relative links with absolute URLs
    --dry-run: Show what would be changed without modifying files
    --validate-links: Check if links are valid by making HTTP requests
    --timeout: Timeout for HTTP requests in seconds (default: 10)
    --url-mapping: Path segment mappings in format old=new (can be used multiple times)
    --ci-mode: CI mode: only report broken links and exit with error code on failures

Note:
    The 'requests' package is required for link validation. Install it with:
    pip install requests
"""

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def find_markdown_files(directory: str) -> List[str]:
    """Find all markdown files in the given directory and its subdirectories."""
    markdown_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))

    return markdown_files


def extract_links_from_markdown(
    file_path: str,
) -> List[Tuple[str, int, str, int, int]]:
    """
    Extract all links from a markdown file along with line numbers and positions.

    Returns list of tuples: (link, line_num, full_line, start_pos, end_pos)
    """
    links = []

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Regular expressions for different types of markdown links
    inline_link_pattern = re.compile(r"\[(?:[^\]]+)\]\(([^)]+)\)")
    reference_link_def_pattern = re.compile(r"^\s*\[(?:[^\]]+)\]:\s*(\S+)")
    html_link_pattern = re.compile(
        r'<a\s+(?:[^>]*?)href=["\'](.*?)["\']', re.IGNORECASE
    )
    bare_url_pattern = re.compile(r"<(https?://[^>]+)>")

    for line_num, line in enumerate(lines, 1):
        # Find inline links [text](url)
        for match in inline_link_pattern.finditer(line):
            url = match.group(1).split()[0]
            start_pos = match.start(1)
            end_pos = start_pos + len(url)

            # Clean URLs with common escape sequences
            # We preserve the original position for proper replacement later
            links.append((url, line_num, line, start_pos, end_pos))

        # Find reference link definitions [id]: url
        for match in reference_link_def_pattern.finditer(line):
            url = match.group(1).split()[0]
            start_pos = match.start(1)
            end_pos = start_pos + len(url)
            links.append((url, line_num, line, start_pos, end_pos))

        # Find HTML links <a href="url">
        for match in html_link_pattern.finditer(line):
            url = match.group(1).split()[0]
            start_pos = match.start(1)
            end_pos = start_pos + len(url)
            links.append((url, line_num, line, start_pos, end_pos))

        # Find bare URLs <http://example.com>
        for match in bare_url_pattern.finditer(line):
            url = match.group(1).split()[0]
            start_pos = match.start(1)
            end_pos = start_pos + len(url)
            links.append((url, line_num, line, start_pos, end_pos))

    return links


def clean_url(url: str) -> str:
    """
    Clean up escaped characters in URLs from markdown files.

    Args:
        url: The URL to clean

    Returns:
        Cleaned URL with escape sequences properly handled
    """
    # Replace escaped underscores with actual underscores
    cleaned = url.replace("\\_", "_")

    # Replace escaped hyphens with actual hyphens
    cleaned = cleaned.replace("\\-", "-")

    # Handle other common escapes in Markdown
    cleaned = cleaned.replace("\\.", ".")
    cleaned = cleaned.replace("\\#", "#")
    cleaned = cleaned.replace("\\(", "(")
    cleaned = cleaned.replace("\\)", ")")

    return cleaned


def check_links_with_substring(
    file_path: str, substring: str
) -> List[Tuple[str, int, str, int, int]]:
    """
    Check links in the file and return those that contain the given substring.
    For internal documentation paths (like 'how-to'), only consider relative links.
    For other substrings, consider all links.

    Args:
        file_path: Path to the markdown file
        substring: Substring to search for in links

    Returns:
        List of tuples: (link, line_num, full_line, start_pos, end_pos)
    """
    links = extract_links_from_markdown(file_path)

    # List of internal documentation paths that should only match relative links
    internal_paths = ["how-to", "user-guide", "component-guide", "book"]

    def should_include_link(link: str) -> bool:
        # Clean the link to properly handle escaped characters
        cleaned_link = clean_url(link)

        if substring not in cleaned_link and substring not in link:
            return False

        # For internal documentation paths, only include relative links
        if substring in internal_paths:
            return link.startswith("../")

        # For other substrings, include all links
        return True

    return [
        (link, line_num, line, start_pos, end_pos)
        for link, line_num, line, start_pos, end_pos in links
        if should_include_link(link)
    ]


def is_local_development_url(url: str) -> bool:
    """Check if a URL is for local development.

    Args:
        url: The URL to check

    Returns:
        bool: True if the URL is for local development, False otherwise
    """
    local_patterns = [
        "http://0.0.0.0",
        "https://0.0.0.0",
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1",
    ]
    return any(url.startswith(pattern) for pattern in local_patterns)


def check_link_validity(
    url: str, timeout: int = 10
) -> Tuple[str, bool, Optional[str], Optional[int]]:
    """
    Check if a URL is valid by making an HTTP request.

    Args:
        url: The URL to check
        timeout: Request timeout in seconds

    Returns:
        Tuple of (url, is_valid, error_message, status_code)
    """
    if not HAS_REQUESTS:
        return url, False, "requests module not installed", None

    # Clean up escaped characters in URLs
    # This helps with Markdown URLs that have escaped underscores, etc.
    cleaned_url = clean_url(url)

    # Skip non-HTTP links
    if not cleaned_url.startswith(("http://", "https://")):
        return url, True, None, None

    # Skip local development URLs
    if is_local_development_url(cleaned_url):
        return url, True, None, None

    # Configure session with retries
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        # First try with HEAD request
        response = session.head(
            cleaned_url, timeout=timeout, allow_redirects=True
        )

        # If HEAD fails, try GET
        if response.status_code >= 400:
            response = session.get(
                cleaned_url, timeout=timeout, allow_redirects=True
            )

        is_valid = response.status_code < 400

        # Additional check for Gitbook URLs that return 200 for non-existent pages
        if is_valid and "docs.zenml.io" in cleaned_url:
            # We need to check for "noindex" meta tag which indicates a 404 page in Gitbook
            try:
                # Use GET to fetch the page content
                content_response = session.get(cleaned_url, timeout=timeout)
                content = content_response.text.lower()

                # Look for the "noindex" meta tag which indicates a 404 page
                if (
                    'name="robots" content="noindex"' in content
                    or 'content="noindex"' in content
                ):
                    return (
                        url,
                        False,
                        "Page returns 200 but contains noindex tag (actual 404)",
                        response.status_code,
                    )
            except requests.RequestException:
                # If we can't check the content, just trust the status code
                pass

        return (
            url,
            is_valid,
            f"HTTP status: {response.status_code}" if not is_valid else None,
            response.status_code,
        )

    except requests.RequestException as e:
        return url, False, str(e), None


def validate_urls(
    urls: List[str], max_workers: int = 10
) -> Dict[str, Tuple[bool, Optional[str], Optional[int]]]:
    """
    Validate multiple URLs in parallel.

    Args:
        urls: List of URLs to validate
        max_workers: Maximum number of parallel workers

    Returns:
        Dictionary of {url: (is_valid, error_message, status_code)}
    """
    results = {}

    print(f"Validating {len(urls)} links...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(check_link_validity, url): url for url in urls
        }

        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                _, is_valid, error_message, status_code = future.result()
                results[url] = (is_valid, error_message, status_code)

                # Print progress indicator
                if i % 10 == 0 or i == len(urls):
                    print(
                        f"  Checked {i}/{len(urls)} links",
                        end="\r",
                        flush=True,
                    )
            except Exception as e:
                results[url] = (False, str(e), None)

    print()  # New line after progress
    return results


def transform_relative_link(
    link: str, url_mappings: Dict[str, str] = None
) -> Optional[str]:
    """
    Transform a relative link to an absolute URL, applying any custom path mappings.

    Examples:
    - "../../how-to/pipeline-development/use-configuration-files/README.md" ->
      "https://docs.zenml.io/how-to/pipeline-development/use-configuration-files"
    - "../../how-to/model-management-metrics/track-metrics-metadata/fetch-metadata-within-pipeline.md" ->
      "https://docs.zenml.io/how-to/model-management-metrics/track-metrics-metadata/fetch-metadata-within-pipeline"

    With url_mappings={"user-guide": "user-guides"}:
    - "../../user-guide/starter-guide/starter-project.md" ->
      "https://docs.zenml.io/user-guides/starter-guide/starter-project"

    Args:
        link: The relative link to transform
        url_mappings: Dictionary of path segment mappings {old: new}

    Returns:
        The absolute URL, or None if the link is not a relative link or doesn't need transformation.
    """
    # Skip links that are already absolute URLs
    if link.startswith(("http://", "https://", "ftp://")):
        return None

    # Skip links that don't start with ../
    if not link.startswith("../"):
        return None

    # Skip links to assets
    clean_test = re.sub(r"^(\.\.\/)+", "", link)
    if "assets" in clean_test or ".gitbook" in clean_test:
        return None

    # Extract the fragment and query parts if present
    fragment = ""
    query = ""

    # Check for query parameters
    if "?" in link:
        link_parts, query = link.split("?", 1)
        link = link_parts
        query = f"?{query}"

    # Check for fragments/anchors
    if "#" in link:
        link_parts, fragment = link.split("#", 1)
        link = link_parts
        fragment = f"#{fragment}"

    # Remove all leading ../ segments
    clean_link = re.sub(r"^(\.\.\/)+", "", link)

    # Handle README.md files
    if clean_link.endswith("/README.md"):
        clean_link = clean_link[:-10]  # Remove '/README.md'
    # Handle normal .md files
    elif clean_link.endswith(".md"):
        clean_link = clean_link[:-3]  # Remove '.md'

    # Apply URL mappings if provided
    if url_mappings:
        for old_path, new_path in url_mappings.items():
            # Match both path/old_path/ and path/old_path (at the start or with slashes)
            pattern = f"(^|/)({re.escape(old_path)})(/?|$|/)"
            clean_link = re.sub(pattern, r"\1" + new_path + r"\3", clean_link)

    # Create absolute URL and add back fragment/query if present
    absolute_url = f"https://docs.zenml.io/{clean_link}{fragment}{query}"

    return absolute_url


def replace_links_in_file(
    file_path: str,
    substring: str,
    dry_run: bool = False,
    validate_links: bool = False,
    url_mappings: Dict[str, str] = None,
) -> Dict[str, Tuple[str, bool, Optional[str]]]:
    """
    Replace relative links in the file with absolute URLs.

    Args:
        file_path: Path to the markdown file
        substring: Substring to search for in links
        dry_run: If True, don't actually modify the file
        validate_links: If True, validate the generated links
        url_mappings: Dictionary of path segment mappings {old: new}

    Returns:
        Dictionary of {original_link: (new_link, is_valid, error_message)}
    """
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    replacements = {}
    transformed_urls = []
    valid_replacements = {}  # Track which replacements are valid

    # Store line-specific replacements
    line_replacements = [[] for _ in range(len(lines))]

    # List of internal documentation paths that should only match relative links
    internal_paths = ["how-to", "user-guide", "component-guide", "book"]

    def should_replace_link(link: str) -> bool:
        if not link.startswith("../"):
            return False

        # Skip links to assets
        if "assets" in link or ".gitbook" in link:
            return False

        if substring is None:
            return True

        # For internal documentation paths, only include relative links that contain the substring
        if substring in internal_paths:
            return substring in link

        # For other substrings, include all links containing the substring
        return substring in link

    # First, collect all potential replacements
    # For inline links and HTML links
    for i, line in enumerate(lines):
        # Regular expressions for different types of markdown links
        patterns = [
            # [text](url)
            (re.compile(r"\[(?:[^\]]+)\]\((\.\./[^)]+)\)"), 1),
            # <a href="url">
            (
                re.compile(
                    r'<a\s+(?:[^>]*?)href=["\'](\.\./.+?)["\']', re.IGNORECASE
                ),
                1,
            ),
        ]

        for pattern, group in patterns:
            for match in pattern.finditer(line):
                relative_link = match.group(group)
                if not should_replace_link(relative_link):
                    continue

                transformed_link = transform_relative_link(
                    relative_link, url_mappings
                )

                if transformed_link:
                    replacements[relative_link] = (
                        transformed_link,
                        None,
                        None,
                    )
                    transformed_urls.append(transformed_link)

                    # Store replacement details for this line (will be applied only if valid)
                    line_replacements[i].append(
                        (
                            match.start(group),  # start position
                            match.end(group),  # end position
                            relative_link,  # original text
                            transformed_link,  # replacement text
                        )
                    )

    # Handle reference-style links
    ref_link_pattern = re.compile(r"^\[([^\]]+)\]:\s*(\.\./\S+)")
    ref_link_replacements = []  # Store reference link replacements
    for i, line in enumerate(lines):
        match = ref_link_pattern.match(line)
        if match:
            ref_id = match.group(1)
            relative_link = match.group(2)
            if not should_replace_link(relative_link):
                continue

            transformed_link = transform_relative_link(
                relative_link, url_mappings
            )

            if transformed_link:
                replacements[relative_link] = (transformed_link, None, None)
                transformed_urls.append(transformed_link)
                ref_link_replacements.append(
                    (i, ref_id, relative_link, transformed_link)
                )

    # Validate links if requested
    validation_results = {}
    if validate_links and transformed_urls:
        validation_results = validate_urls(transformed_urls)

        # Update the replacements dictionary with validation results
        for rel_link, (trans_link, _, _) in replacements.items():
            if trans_link in validation_results:
                is_valid, error_message, _ = validation_results[trans_link]
                replacements[rel_link] = (trans_link, is_valid, error_message)
                # Mark which replacements are valid
                if is_valid:
                    valid_replacements[rel_link] = trans_link

    # If not validating, all replacements are considered valid
    if not validate_links:
        for rel_link, (trans_link, _, _) in replacements.items():
            valid_replacements[rel_link] = trans_link

    # Only apply replacements that are valid (or all if not validating)
    if not dry_run:
        modified = False

        # Apply reference link replacements
        for (
            i,
            ref_id,
            relative_link,
            transformed_link,
        ) in ref_link_replacements:
            # Only replace if valid or not validating
            if relative_link in valid_replacements:
                new_line = f"[{ref_id}]: {transformed_link}\n"
                lines[i] = new_line
                modified = True

        # Apply inline and HTML link replacements
        for i, line_replace_data in enumerate(line_replacements):
            if line_replace_data:
                # Filter to only valid replacements
                valid_line_replacements = [
                    (start_pos, end_pos, original, replacement)
                    for start_pos, end_pos, original, replacement in line_replace_data
                    if original in valid_replacements
                ]

                if valid_line_replacements:
                    # Sort replacements right-to-left (by start position, descending)
                    valid_line_replacements.sort(
                        key=lambda x: x[0], reverse=True
                    )

                    # Apply all valid replacements for this line
                    line_text = lines[i]
                    for (
                        start_pos,
                        end_pos,
                        original,
                        replacement,
                    ) in valid_line_replacements:
                        line_text = (
                            line_text[:start_pos]
                            + replacement
                            + line_text[end_pos:]
                        )

                    lines[i] = line_text
                    modified = True

        # Write the modified content back to the file
        if modified:
            with open(file_path, "w", encoding="utf-8") as file:
                file.writelines(lines)

    return replacements


def get_clickable_path(file_path: str, line_num: int) -> str:
    """
    Generate a clickable path for the terminal.

    This creates links that work in most terminals and editors to directly open
    the file at the specified line when clicked.
    """
    # Get absolute path
    abs_path = os.path.abspath(file_path)

    # Create a clickable link format that works in many terminals
    # We provide multiple formats to increase compatibility across different terminals/editors
    standard_format = f"{abs_path}:{line_num}"
    vscode_format = f"file://{abs_path}:{line_num}"

    return f"{standard_format} (VSCode: {vscode_format})"


def main():
    parser = argparse.ArgumentParser(
        description="Check and replace markdown links."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dir", help="Directory containing markdown files to scan"
    )
    group.add_argument(
        "--files", nargs="+", help="List of markdown files to scan"
    )
    parser.add_argument("--substring", help="Substring to search for in links")
    parser.add_argument(
        "--replace-links",
        action="store_true",
        help="Replace relative links with absolute URLs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--validate-links",
        action="store_true",
        help="Check if links are valid by making HTTP requests",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for HTTP requests in seconds (default: 10)",
    )
    parser.add_argument(
        "--url-mapping",
        action="append",
        help="Path segment mappings in format old=new (can be used multiple times)",
    )
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI mode: only report broken links and exit with error code on failures",
    )
    args = parser.parse_args()

    # Check for requests module if validation is enabled
    if args.validate_links and not HAS_REQUESTS:
        print("Error: Link validation requires the 'requests' package.")
        print("Please install it with: pip install requests")
        sys.exit(1)

    if not args.substring and not args.replace_links:
        parser.error("Either --substring or --replace-links must be specified")

    # Process URL mappings if provided
    url_mappings = {}
    if args.url_mapping:
        for mapping in args.url_mapping:
            try:
                old, new = mapping.split("=", 1)
                url_mappings[old] = new
            except ValueError:
                print(
                    f"Warning: Invalid URL mapping format: {mapping}. Expected format: old=new"
                )

    files_to_scan = []
    if args.dir:
        files_to_scan = find_markdown_files(args.dir)
        if not args.ci_mode:
            print(
                f"Found {len(files_to_scan)} markdown files in directory: {args.dir}"
            )
    else:
        files_to_scan = args.files
        if not args.ci_mode:
            print(f"Scanning {len(files_to_scan)} specified markdown files")

    if args.replace_links:
        # Replace links mode
        total_replacements = 0
        valid_links = 0
        broken_links = 0

        for file_path in files_to_scan:
            try:
                replacements = replace_links_in_file(
                    file_path,
                    args.substring,
                    args.dry_run,
                    args.validate_links,
                    url_mappings,
                )
                if replacements:
                    if not args.ci_mode:
                        print(f"\n{file_path}:")
                    for original, (
                        new,
                        is_valid,
                        error,
                    ) in replacements.items():
                        total_replacements += 1

                        if args.validate_links and is_valid is not None:
                            if is_valid:
                                valid_links += 1
                                if not args.ci_mode:
                                    print(f"  {original} -> {new} [✅ Valid]")
                            else:
                                broken_links += 1
                                # Always print broken links even in CI mode
                                status = f"❌ Broken: {error}"
                                if args.ci_mode:
                                    print(f"{file_path}:")
                                print(f"  {original} -> {new} [{status}]")
                        elif not args.ci_mode:
                            print(f"  {original} -> {new}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)

        mode = "Would replace" if args.dry_run else "Replaced"
        if not args.ci_mode:
            print(
                f"\n{mode} {total_replacements} links across {len(files_to_scan)} files."
            )

            if args.validate_links and (valid_links > 0 or broken_links > 0):
                print(
                    f"Link validation: {valid_links} valid, {broken_links} broken"
                )

        # In CI mode, exit with error code if broken links were found
        if args.ci_mode and broken_links > 0:
            print(f"\nFound {broken_links} broken links")
            sys.exit(1)

    elif args.substring:
        # Find links mode
        total_matches = 0
        links_to_validate = []
        file_links_map = {}
        has_broken_links = False

        for file_path in files_to_scan:
            try:
                matches = check_links_with_substring(file_path, args.substring)
                if matches:
                    file_links = []
                    if not args.ci_mode:
                        print(f"\n{file_path}:")
                    for link, line_num, _, _, _ in matches:
                        # Create clickable link to the file at the specific line
                        clickable_path = get_clickable_path(
                            file_path, line_num
                        )

                        if not args.ci_mode:
                            print(f"  Line {line_num}: {link}")
                            print(f"    ↳ {clickable_path}")

                        total_matches += 1

                        if args.validate_links:
                            # For relative links, transform them to absolute URLs first
                            if link.startswith("../"):
                                transformed_link = transform_relative_link(
                                    link, url_mappings
                                )
                                if transformed_link:
                                    links_to_validate.append(transformed_link)
                                    file_links.append(
                                        (transformed_link, line_num, link)
                                    )  # Store original link too
                            # For absolute links, validate directly
                            elif link.startswith(("http://", "https://")):
                                links_to_validate.append(link)
                                file_links.append(
                                    (link, line_num, link)
                                )  # Original and transformed are the same
                            # If neither, log it but don't validate
                            elif not args.ci_mode:
                                print(
                                    f"    ↳ Skipping validation (not a recognized link format)"
                                )

                    if file_links:
                        file_links_map[file_path] = file_links
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)

        if not args.ci_mode:
            print(
                f"\nFound {total_matches} links containing '{args.substring}' across {len(files_to_scan)} files."
            )

        # Validate links if requested
        if args.validate_links and links_to_validate:
            if not args.ci_mode:
                print(f"\nValidating {len(links_to_validate)} links...")
            validation_results = validate_urls(list(set(links_to_validate)))

            valid_count = sum(
                1 for result in validation_results.values() if result[0]
            )
            broken_count = len(validation_results) - valid_count

            if not args.ci_mode:
                print(
                    f"\nLink validation: {valid_count} valid, {broken_count} broken"
                )

            if broken_count > 0:
                has_broken_links = True
                if not args.ci_mode:
                    print("\nBroken links:")

                for file_path, links in file_links_map.items():
                    broken_in_file = []
                    for transformed_link, line_num, original_link in links:
                        if (
                            transformed_link in validation_results
                            and not validation_results[transformed_link][0]
                        ):
                            broken_in_file.append(
                                (transformed_link, line_num, original_link)
                            )

                    if broken_in_file:
                        print(f"\n{file_path}:")
                        for (
                            transformed_link,
                            line_num,
                            original_link,
                        ) in broken_in_file:
                            is_valid, error, status_code = validation_results[
                                transformed_link
                            ]
                            status_info = (
                                f"Status: {status_code}"
                                if status_code
                                else error
                            )
                            # Show the original link in the output, but we validated the transformed one
                            print(f"  Line {line_num}: {original_link}")
                            print(f"    ↳ ❌ {status_info}")

                            # Always show what URL was actually validated
                            cleaned_url = clean_url(original_link)
                            if cleaned_url != original_link:
                                print(
                                    f"    ↳ URL with escapes removed: {cleaned_url}"
                                )
                            if (
                                original_link != transformed_link
                                and cleaned_url != transformed_link
                                and not args.ci_mode
                            ):
                                print(
                                    f"    ↳ Validated as: {transformed_link}"
                                )

                            clickable_path = get_clickable_path(
                                file_path, line_num
                            )
                            print(f"    ↳ {clickable_path}")

        # In CI mode, exit with error code if broken links were found
        if args.ci_mode and has_broken_links:
            sys.exit(1)


if __name__ == "__main__":
    main()
