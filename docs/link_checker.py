#!/usr/bin/env python3
"""
Link Checker Script

This script scans markdown files for links and detects if they contain a specified substring.
It can process either a directory of markdown files or a list of specific files.
It can also replace relative links with absolute URLs.
It can validate links by making HTTP requests to check if they are broken.

Usage:
    python link_checker.py --dir docs/book --substring docs.zenml.io
    python link_checker.py --files file1.md file2.md --substring docs.zenml.io
    python link_checker.py --files file1.md --replace-links --dry-run
    python link_checker.py --files file1.md --replace-links --validate-links
"""

import argparse
import os
import re
import sys
import time
from typing import List, Set, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
    
    return markdown_files


def extract_links_from_markdown(file_path: str) -> List[Tuple[str, int, str, int, int]]:
    """
    Extract all links from a markdown file along with line numbers and positions.
    
    Returns list of tuples: (link, line_num, full_line, start_pos, end_pos)
    """
    links = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    # Regular expressions for different types of markdown links
    inline_link_pattern = re.compile(r'\[(?:[^\]]+)\]\(([^)]+)\)')
    reference_link_def_pattern = re.compile(r'^\s*\[(?:[^\]]+)\]:\s*(\S+)')
    html_link_pattern = re.compile(r'<a\s+(?:[^>]*?)href=["\'](.*?)["\']', re.IGNORECASE)
    bare_url_pattern = re.compile(r'<(https?://[^>]+)>')
    
    for line_num, line in enumerate(lines, 1):
        # Find inline links [text](url)
        for match in inline_link_pattern.finditer(line):
            url = match.group(1).split()[0]
            start_pos = match.start(1)
            end_pos = start_pos + len(url)
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


def check_links_with_substring(file_path: str, substring: str) -> List[Tuple[str, int, str, int, int]]:
    """Check links in the file and return those that contain the given substring."""
    links = extract_links_from_markdown(file_path)
    return [(link, line_num, line, start_pos, end_pos) for link, line_num, line, start_pos, end_pos in links if substring in link]


def check_link_validity(url: str, timeout: int = 10) -> Tuple[str, bool, Optional[str], Optional[int]]:
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
    
    # Skip non-HTTP links
    if not url.startswith(('http://', 'https://')):
        return url, True, None, None
    
    # Configure session with retries
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    try:
        # First try with HEAD request
        response = session.head(url, timeout=timeout, allow_redirects=True)
        
        # If HEAD fails, try GET
        if response.status_code >= 400:
            response = session.get(url, timeout=timeout, allow_redirects=True)
        
        is_valid = response.status_code < 400
        return url, is_valid, f"HTTP status: {response.status_code}" if not is_valid else None, response.status_code
    
    except requests.RequestException as e:
        return url, False, str(e), None


def validate_urls(urls: List[str], max_workers: int = 10) -> Dict[str, Tuple[bool, Optional[str], Optional[int]]]:
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
        future_to_url = {executor.submit(check_link_validity, url): url for url in urls}
        
        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                _, is_valid, error_message, status_code = future.result()
                results[url] = (is_valid, error_message, status_code)
                
                # Print progress indicator
                if i % 10 == 0 or i == len(urls):
                    print(f"  Checked {i}/{len(urls)} links", end="\r", flush=True)
            except Exception as e:
                results[url] = (False, str(e), None)
    
    print()  # New line after progress
    return results


def transform_relative_link(link: str) -> Optional[str]:
    """
    Transform a relative link to an absolute URL.
    
    Examples:
    - "../../how-to/pipeline-development/use-configuration-files/README.md" -> 
      "https://docs.zenml.io/how-to/pipeline-development/use-configuration-files"
    - "../../how-to/model-management-metrics/track-metrics-metadata/fetch-metadata-within-pipeline.md" ->
      "https://docs.zenml.io/how-to/model-management-metrics/track-metrics-metadata/fetch-metadata-within-pipeline"
    
    Returns None if the link is not a relative link or doesn't need transformation.
    """
    # Skip links that are already absolute URLs
    if link.startswith(('http://', 'https://', 'ftp://')):
        return None
    
    # Skip links that don't start with ../
    if not link.startswith('../'):
        return None
    
    # Extract the fragment and query parts if present
    fragment = ""
    query = ""
    
    # Check for query parameters
    if '?' in link:
        link_parts, query = link.split('?', 1)
        link = link_parts
        query = f"?{query}"
    
    # Check for fragments/anchors
    if '#' in link:
        link_parts, fragment = link.split('#', 1)
        link = link_parts
        fragment = f"#{fragment}"
    
    # Remove all leading ../ segments
    clean_link = re.sub(r'^(\.\.\/)+', '', link)
    
    # Handle README.md files
    if clean_link.endswith('/README.md'):
        clean_link = clean_link[:-10]  # Remove '/README.md'
    # Handle normal .md files    
    elif clean_link.endswith('.md'):
        clean_link = clean_link[:-3]  # Remove '.md'
    
    # Create absolute URL and add back fragment/query if present
    absolute_url = f"https://docs.zenml.io/{clean_link}{fragment}{query}"
    
    return absolute_url


def replace_links_in_file(file_path: str, dry_run: bool = False, validate_links: bool = False) -> Dict[str, Tuple[str, bool, Optional[str]]]:
    """
    Replace relative links in the file with absolute URLs.
    
    Args:
        file_path: Path to the markdown file
        dry_run: If True, don't actually modify the file
        validate_links: If True, validate the generated links
        
    Returns:
        Dictionary of {original_link: (new_link, is_valid, error_message)}
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    replacements = {}
    transformed_urls = []
    modified = False
    
    # First, handle inline links and HTML links
    for i, line in enumerate(lines):
        # Regular expressions for different types of markdown links
        patterns = [
            # [text](url)
            (re.compile(r'\[(?:[^\]]+)\]\((\.\./[^)]+)\)'), 1),
            # <a href="url">
            (re.compile(r'<a\s+(?:[^>]*?)href=["\'](\.\./.+?)["\']', re.IGNORECASE), 1),
        ]
        
        for pattern, group in patterns:
            for match in pattern.finditer(line):
                relative_link = match.group(group)
                transformed_link = transform_relative_link(relative_link)
                
                if transformed_link:
                    replacements[relative_link] = (transformed_link, None, None)
                    transformed_urls.append(transformed_link)
                    
                    # Only actually replace if not in dry run mode
                    if not dry_run:
                        new_line = line.replace(relative_link, transformed_link)
                        lines[i] = new_line
                        modified = True
    
    # Handle reference-style links
    ref_link_pattern = re.compile(r'^\[([^\]]+)\]:\s*(\.\./\S+)')
    for i, line in enumerate(lines):
        match = ref_link_pattern.match(line)
        if match:
            ref_id = match.group(1)
            relative_link = match.group(2)
            transformed_link = transform_relative_link(relative_link)
            
            if transformed_link:
                replacements[relative_link] = (transformed_link, None, None)
                transformed_urls.append(transformed_link)
                
                # Only actually replace if not in dry run mode
                if not dry_run:
                    new_line = f"[{ref_id}]: {transformed_link}\n" if not line.endswith("\n") else f"[{ref_id}]: {transformed_link}\n"
                    lines[i] = new_line
                    modified = True
    
    # Write the modified content back to the file
    if not dry_run and modified:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
    
    # Validate links if requested
    if validate_links and transformed_urls:
        validation_results = validate_urls(transformed_urls)
        
        # Update the replacements dictionary with validation results
        for rel_link, (trans_link, _, _) in replacements.items():
            if trans_link in validation_results:
                is_valid, error_message, _ = validation_results[trans_link]
                replacements[rel_link] = (trans_link, is_valid, error_message)
    
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
    parser = argparse.ArgumentParser(description='Check and replace markdown links.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dir', help='Directory containing markdown files to scan')
    group.add_argument('--files', nargs='+', help='List of markdown files to scan')
    parser.add_argument('--substring', help='Substring to search for in links')
    parser.add_argument('--replace-links', action='store_true', help='Replace relative links with absolute URLs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--validate-links', action='store_true', help='Check if links are valid by making HTTP requests')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for HTTP requests in seconds (default: 10)')
    args = parser.parse_args()
    
    # Check for requests module if validation is enabled
    if args.validate_links and not HAS_REQUESTS:
        print("Error: Link validation requires the 'requests' package.")
        print("Please install it with: pip install requests")
        sys.exit(1)
    
    if not args.substring and not args.replace_links:
        parser.error("Either --substring or --replace-links must be specified")
    
    files_to_scan = []
    if args.dir:
        files_to_scan = find_markdown_files(args.dir)
        print(f"Found {len(files_to_scan)} markdown files in directory: {args.dir}")
    else:
        files_to_scan = args.files
        print(f"Scanning {len(files_to_scan)} specified markdown files")
    
    if args.replace_links:
        # Replace links mode
        total_replacements = 0
        valid_links = 0
        broken_links = 0
        
        for file_path in files_to_scan:
            try:
                replacements = replace_links_in_file(file_path, args.dry_run, args.validate_links)
                if replacements:
                    print(f"\n{file_path}:")
                    for original, (new, is_valid, error) in replacements.items():
                        total_replacements += 1
                        
                        if args.validate_links and is_valid is not None:
                            status = "✅ Valid" if is_valid else f"❌ Broken: {error}"
                            print(f"  {original} -> {new} [{status}]")
                            
                            if is_valid:
                                valid_links += 1
                            else:
                                broken_links += 1
                        else:
                            print(f"  {original} -> {new}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)
        
        mode = "Would replace" if args.dry_run else "Replaced"
        print(f"\n{mode} {total_replacements} links across {len(files_to_scan)} files.")
        
        if args.validate_links and (valid_links > 0 or broken_links > 0):
            print(f"Link validation: {valid_links} valid, {broken_links} broken")
    
    elif args.substring:
        # Find links mode
        total_matches = 0
        links_to_validate = []
        file_links_map = {}
        
        for file_path in files_to_scan:
            try:
                matches = check_links_with_substring(file_path, args.substring)
                if matches:
                    file_links = []
                    print(f"\n{file_path}:")
                    for link, line_num, _, _, _ in matches:
                        # Create clickable link to the file at the specific line
                        clickable_path = get_clickable_path(file_path, line_num)
                        print(f"  Line {line_num}: {link}")
                        print(f"    ↳ {clickable_path}")
                        total_matches += 1
                        
                        if args.validate_links:
                            # For relative links, transform them to absolute URLs first
                            if link.startswith('../'):
                                transformed_link = transform_relative_link(link)
                                if transformed_link:
                                    links_to_validate.append(transformed_link)
                                    file_links.append((transformed_link, line_num, link))  # Store original link too
                            # For absolute links, validate directly
                            elif link.startswith(('http://', 'https://')):
                                links_to_validate.append(link)
                                file_links.append((link, line_num, link))  # Original and transformed are the same
                            # If neither, log it but don't validate
                            else:
                                print(f"    ↳ Skipping validation (not a recognized link format)")
                    
                    if file_links:
                        file_links_map[file_path] = file_links
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)
        
        print(f"\nFound {total_matches} links containing '{args.substring}' across {len(files_to_scan)} files.")
        
        # Validate links if requested
        if args.validate_links and links_to_validate:
            print(f"\nValidating {len(links_to_validate)} links...")
            validation_results = validate_urls(list(set(links_to_validate)))
            
            valid_count = sum(1 for result in validation_results.values() if result[0])
            broken_count = len(validation_results) - valid_count
            
            print(f"\nLink validation: {valid_count} valid, {broken_count} broken")
            
            if broken_count > 0:
                print("\nBroken links:")
                for file_path, links in file_links_map.items():
                    broken_in_file = []
                    for transformed_link, line_num, original_link in links:
                        if transformed_link in validation_results and not validation_results[transformed_link][0]:
                            broken_in_file.append((transformed_link, line_num, original_link))
                    
                    if broken_in_file:
                        print(f"\n{file_path}:")
                        for transformed_link, line_num, original_link in broken_in_file:
                            is_valid, error, status_code = validation_results[transformed_link]
                            status_info = f"Status: {status_code}" if status_code else error
                            # Show the original link in the output, but we validated the transformed one
                            print(f"  Line {line_num}: {original_link}")
                            print(f"    ↳ ❌ {status_info}")
                            if original_link != transformed_link:
                                print(f"    ↳ Validated as: {transformed_link}")
                            clickable_path = get_clickable_path(file_path, line_num)
                            print(f"    ↳ {clickable_path}")


if __name__ == "__main__":
    main() 