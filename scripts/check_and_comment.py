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

    # Calculate statistics
    total_files = len({link["source_file"] for link in broken_links})
    total_broken = len(broken_links)

    body = [
        "# 🔍 Broken Links Report",
        "",
        "### Summary",
        f"- 📁 Files with broken links: **{total_files}**",
        f"- 🔗 Total broken links: **{total_broken}**",
        "",
        "### Details",
        "| File | Link Text | Broken Path |",
        "|------|-----------|-------------|",
    ]

    # Add each broken link as a table row
    for link in broken_links:
        file_name = Path(link["source_file"]).name
        full_path = link["source_file"]
        body.append(
            f"| `{file_name}` | \"{link['link_text']}\" | `{link['broken_path']}` |"
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
    if "GITHUB_TOKEN" in os.environ:
        # Only import github when needed
        from github import Github

        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN not set")
            sys.exit(1)

        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            event = json.load(f)

        repo_name = event["repository"]["full_name"]
        pr_number = event["pull_request"]["number"]

        g = Github(token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        comment_body = create_comment_body(broken_links)

        for comment in pr.get_issue_comments():
            if (
                "Broken Links Found" in comment.body
                or "No broken markdown links found!" in comment.body
            ):
                comment.edit(comment_body)
                break
        else:
            pr.create_issue_comment(comment_body)

    # Always print results locally
    if not broken_links:
        print("✅ No broken links found!")
        sys.exit(0)

    print("\n🔍 Broken links found:")
    for link in broken_links:
        relative_path = format_path_for_display(link["source_file"])
        print(f"\n📄 File: {relative_path}")
        print(f"📝 Link text: \"{link['link_text']}\"")
        print(f"❌ Broken path: {link['broken_path']}")

    sys.exit(1)


if __name__ == "__main__":
    main()
