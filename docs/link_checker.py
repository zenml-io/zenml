#!/usr/bin/env python3
"""
Link Checker Script

This script scans markdown files for links and detects if they contain a specified substring.
It can process either a directory of markdown files or a list of specific files.

Usage:
    python link_checker.py --dir docs/book --substring docs.zenml.io
    python link_checker.py --files file1.md file2.md --substring docs.zenml.io
"""

import argparse
import os
import re
import sys
from typing import List, Set, Tuple


def find_markdown_files(directory: str) -> List[str]:
    """Find all markdown files in the given directory and its subdirectories."""
    markdown_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
    
    return markdown_files


def extract_links_from_markdown(file_path: str) -> List[Tuple[str, int]]:
    """Extract all links from a markdown file along with line numbers."""
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
            links.append((match.group(1).split()[0], line_num))
        
        # Find reference link definitions [id]: url
        for match in reference_link_def_pattern.finditer(line):
            links.append((match.group(1).split()[0], line_num))
        
        # Find HTML links <a href="url">
        for match in html_link_pattern.finditer(line):
            links.append((match.group(1).split()[0], line_num))
        
        # Find bare URLs <http://example.com>
        for match in bare_url_pattern.finditer(line):
            links.append((match.group(1).split()[0], line_num))
    
    return links


def check_links_with_substring(file_path: str, substring: str) -> List[Tuple[str, int]]:
    """Check links in the file and return those that contain the given substring."""
    links = extract_links_from_markdown(file_path)
    return [(link, line_num) for link, line_num in links if substring in link]


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
    parser = argparse.ArgumentParser(description='Check markdown links containing a specific substring.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dir', help='Directory containing markdown files to scan')
    group.add_argument('--files', nargs='+', help='List of markdown files to scan')
    parser.add_argument('--substring', required=True, help='Substring to search for in links')
    args = parser.parse_args()
    
    files_to_scan = []
    if args.dir:
        files_to_scan = find_markdown_files(args.dir)
        print(f"Found {len(files_to_scan)} markdown files in directory: {args.dir}")
    else:
        files_to_scan = args.files
        print(f"Scanning {len(files_to_scan)} specified markdown files")
    
    total_matches = 0
    
    for file_path in files_to_scan:
        try:
            matches = check_links_with_substring(file_path, args.substring)
            if matches:
                print(f"\n{file_path}:")
                for link, line_num in matches:
                    # Create clickable link to the file at the specific line
                    clickable_path = get_clickable_path(file_path, line_num)
                    print(f"  Line {line_num}: {link}")
                    print(f"    ↳ {clickable_path}")
                    total_matches += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
    
    print(f"\nFound {total_matches} links containing '{args.substring}' across {len(files_to_scan)} files.")


if __name__ == "__main__":
    main() 