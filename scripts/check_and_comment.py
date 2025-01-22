import json
import os
import re
import sys
from pathlib import Path

from github import Github


def find_markdown_files(directory):
    """Recursively find all markdown files in a directory."""
    return list(Path(directory).rglob("*.md"))


def extract_relative_links(content):
    """Extract all relative markdown links from content."""
    # Match [text](path.md) or [text](../path.md) patterns
    # Excluding URLs (http:// or https://)
    pattern = r"\[([^\]]+)\]\((?!http[s]?://)(.[^\)]+\.md)\)"
    matches = re.finditer(pattern, content)
    return [(m.group(1), m.group(2)) for m in matches]


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

            for link_text, link_path in relative_links:
                if not validate_link(file_path, link_path):
                    broken_links.append(
                        {
                            "source_file": str(file_path),
                            "link_text": link_text,
                            "broken_path": link_path,
                        }
                    )
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    return broken_links


def create_comment_body(broken_links):
    if not broken_links:
        return "✅ No broken markdown links found!"

    body = "## 🔍 Broken Markdown Links Found\n\n"
    for link in broken_links:
        body += f"### In file: `{link['source_file']}`\n"
        body += f"- Link text: \"{link['link_text']}\"\n"
        body += f"- Broken path: `{link['broken_path']}`\n\n"

    return body


def main():
    # Check if running from GitHub Actions
    if "GITHUB_TOKEN" in os.environ:
        # Get GitHub token and context
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN not set")
            sys.exit(1)

        # Parse GitHub context
        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            event = json.load(f)

        repo_name = event["repository"]["full_name"]
        pr_number = event["pull_request"]["number"]

        # Initialize GitHub client
        g = Github(token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        # Check for broken links in the docs directory
        docs_dir = Path(__file__).parent.parent / "docs"
        broken_links = check_markdown_links(str(docs_dir))

        # Create and post comment
        comment_body = create_comment_body(broken_links)

        # Check if we already commented
        for comment in pr.get_issue_comments():
            if (
                "Broken Markdown Links Found" in comment.body
                or "No broken markdown links found!" in comment.body
            ):
                comment.edit(comment_body)
                break
        else:
            pr.create_issue_comment(comment_body)

        # Exit with error if broken links were found
        if broken_links:
            sys.exit(1)

    else:
        # Running locally
        if len(sys.argv) != 2:
            print("Usage: python check_and_comment.py <directory>")
            sys.exit(1)

        directory = sys.argv[1]
        if not os.path.isdir(directory):
            print(f"Error: {directory} is not a valid directory")
            sys.exit(1)

        print(f"Checking markdown links in {directory}...")
        broken_links = check_markdown_links(directory)

        if not broken_links:
            print("No broken links found!")
            return

        print("\nBroken links found:")
        for link in broken_links:
            print(f"\nSource file: {link['source_file']}")
            print(f"Link text: {link['link_text']}")
            print(f"Broken path: {link['broken_path']}")


if __name__ == "__main__":
    main()
