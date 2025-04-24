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
"""Checks for broken markdown links in a directory and comments on a PR if found."""

import json
import os
import re
import sys
from pathlib import Path


def format_path_for_display(path):
    """Convert absolute path to relative path from repo root."""
    try:
        # Get the repo root (parent of scripts directory)
        repo_root = Path(__file__).parent.parent
        # First resolve the path to remove any ../ components
        full_path = Path(path).resolve()
        return str(full_path.relative_to(repo_root))
    except ValueError:
        # If path is not relative to repo root, return as is
        return str(path)


def find_markdown_files(directory):
    """Recursively find all markdown files in a directory."""
    return list(Path(directory).rglob("*.md"))


def extract_relative_links(content):
    """Extract all relative markdown links from content."""
    links = []

    # Match [text](path.md) or [text](../path.md) patterns
    # Excluding URLs (http:// or https://)
    md_pattern = r"\[([^\]]+)\]\((?!http[s]?://)(.[^\)]+\.md)\)"
    md_matches = re.finditer(md_pattern, content)
    links.extend([(m.group(1), m.group(2), "markdown") for m in md_matches])

    # Match ![text](path.png) or ![text](../path.jpg) patterns for images
    # Excluding URLs (http:// or https://)
    img_pattern = r"!\[([^\]]*)\]\((?!http[s]?://)(.[^\)]+\.(png|jpg|jpeg|gif|svg|webp))\)"
    img_matches = re.finditer(img_pattern, content)
    links.extend([(m.group(1), m.group(2), "image") for m in img_matches])

    # Match [text](broken-reference) patterns
    broken_ref_pattern = r"\[([^\]]+)\]\(broken-reference\)"
    broken_ref_matches = re.finditer(broken_ref_pattern, content)
    links.extend(
        [
            (m.group(1), "broken-reference", "broken-reference")
            for m in broken_ref_matches
        ]
    )

    return links


def validate_link(source_file, target_path):
    """Validate if a relative link is valid."""
    try:
        # Convert source file and target path to Path objects
        source_dir = Path(source_file).parent
        # Resolve the target path relative to the source file's directory
        full_path = (source_dir / target_path).resolve()
        return full_path.exists()
    except Exception:
        return False


def check_markdown_links(directory):
    """Check all markdown files in directory for broken relative links."""
    broken_links = []
    markdown_files = find_markdown_files(directory)

    for file_path in markdown_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            relative_links = extract_relative_links(content)

            for link_text, link_path, link_type in relative_links:
                # Automatically consider broken-reference links as broken
                if link_type == "broken-reference":
                    broken_links.append(
                        {
                            "source_file": str(file_path),
                            "link_text": link_text,
                            "broken_path": link_path,
                            "link_type": "markdown",  # Categorize as markdown for statistics
                        }
                    )
                elif not validate_link(file_path, link_path):
                    broken_links.append(
                        {
                            "source_file": str(file_path),
                            "link_text": link_text,
                            "broken_path": link_path,
                            "link_type": link_type,
                        }
                    )
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    return broken_links


def create_comment_body(broken_links):
    if not broken_links:
        return "✅ No broken links found!"

    # Calculate statistics
    total_files = len({link["source_file"] for link in broken_links})
    total_broken = len(broken_links)
    md_links = sum(
        1
        for link in broken_links
        if link["link_type"] == "markdown"
        and link["broken_path"] != "broken-reference"
    )
    img_links = sum(1 for link in broken_links if link["link_type"] == "image")
    broken_ref_links = sum(
        1 for link in broken_links if link["broken_path"] == "broken-reference"
    )

    body = [
        "# 🔍 Broken Links Report",
        "",
        "### Summary",
        f"- 📁 Files with broken links: **{total_files}**",
        f"- 🔗 Total broken links: **{total_broken}**",
        f"- 📄 Broken markdown links: **{md_links}**",
        f"- 🖼️ Broken image links: **{img_links}**",
        f"- ⚠️ Broken reference placeholders: **{broken_ref_links}**",
        "",
        "### Details",
        "| File | Link Type | Link Text | Broken Path |",
        "|------|-----------|-----------|-------------|",
    ]

    # Add each broken link as a table row
    for link in broken_links:
        # Get parent folder and file name
        path = Path(link["source_file"])
        parent = path.parent.name
        file_name = path.name
        display_name = (
            f"{parent}/{file_name}"  # Combine parent folder and filename
        )

        # Use emoji to indicate link type
        if link["broken_path"] == "broken-reference":
            link_type_icon = "⚠️"  # Warning icon for broken-reference
        else:
            link_type_icon = "📄" if link["link_type"] == "markdown" else "🖼️"

        body.append(
            f'| `{display_name}` | {link_type_icon} | "{link["link_text"]}" | `{link["broken_path"]}` |'
        )

    body.append("")
    body.append("<details><summary>📂 Full file paths</summary>")
    body.append("")
    for link in broken_links:
        body.append(f"- `{link['source_file']}`")
    body.append("")
    body.append("</details>")

    return "\n".join(body)


def main():
    # Get the directory to check from command line argument
    if len(sys.argv) != 2:
        print("Usage: python check_and_comment.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    print(f"Checking markdown links in {directory}...")
    broken_links = check_markdown_links(directory)

    # If running in GitHub Actions, handle PR comment
    if token := os.environ.get("GITHUB_TOKEN"):
        # Only import github when needed
        from github import Github

        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            event = json.load(f)

        repo_name = event["repository"]["full_name"]
        pr_number = event["pull_request"]["number"]

        g = Github(token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        comment_body = create_comment_body(broken_links)

        # Find existing comment by looking for our specific header
        existing_comment = None
        for comment in pr.get_issue_comments():
            if (
                "# 🔍 Broken Links Report" in comment.body
                or "✅ No broken markdown links found!" in comment.body
            ):
                existing_comment = comment
                break

        # Update existing comment or create new one
        if existing_comment:
            existing_comment.edit(comment_body)
            print("Updated existing broken links report comment")
        elif broken_links:
            pr.create_issue_comment(comment_body)
            print("Created new broken links report comment")

        # In GitHub Actions, always exit with 0 after commenting
        sys.exit(0)

    # For local runs, print results and exit with appropriate code
    if not broken_links:
        print("✅ No broken links found!")
        sys.exit(0)

    print("\n🔍 Broken links found:")
    for link in broken_links:
        relative_path = format_path_for_display(link["source_file"])
        if link["broken_path"] == "broken-reference":
            link_type = "Broken reference placeholder"
        else:
            link_type = "Image" if link["link_type"] == "image" else "Markdown"
        print(f"\n📄 File: {relative_path}")
        print(f"🔗 Type: {link_type}")
        print(f'📝 Link text: "{link["link_text"]}"')
        print(f"❌ Broken path: {link['broken_path']}")

    # Only exit with error code in local mode
    sys.exit(1)


if __name__ == "__main__":
    main()
