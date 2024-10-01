import os
import sys
import re
from typing import List, Tuple


def is_relative_link(link: str) -> bool:
    return not link.startswith(("http://", "https://", "/", "#"))


def check_file_for_relative_links(file_path: str) -> List[Tuple[int, str]]:
    relative_links = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line_num, line in enumerate(file, 1):
            links = re.findall(r"\[.*?\]\((.*?)\)", line)
            relative_links.extend(
                (line_num, link) for link in links if is_relative_link(link)
            )
    return relative_links


def process_directory(
    directory: str,
) -> List[Tuple[str, List[Tuple[int, str]]]]:
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith((".md", ".mdx")):
                file_path = os.path.join(root, file)
                if relative_links := check_file_for_relative_links(file_path):
                    results.append((file_path, relative_links))
    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_or_file>")
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isdir(path):
        results = process_directory(path)
    elif os.path.isfile(path) and path.endswith((".md", ".mdx")):
        results = [(path, check_file_for_relative_links(path))]
    else:
        print(f"Error: '{path}' is not a valid directory or .md/.mdx file.")
        sys.exit(1)

    if results:
        print("Relative links found:")
        for file_path, links in results:
            print(f"\nFile: {file_path}")
            for line_num, link in links:
                print(f"  Line {line_num}: {link}")
        print("\nPlease convert all relative links to absolute links.")
        sys.exit(1)
    else:
        print("No relative links found. All links are absolute.")


if __name__ == "__main__":
    main()
