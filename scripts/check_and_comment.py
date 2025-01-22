import json
import os
import sys
from pathlib import Path

from github import Github

# Add the docs/book directory to the Python path so we can import brokelinks
sys.path.append(str(Path(__file__).parent.parent / "docs" / "book"))
from brokelinks import check_markdown_links


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


if __name__ == "__main__":
    main()
