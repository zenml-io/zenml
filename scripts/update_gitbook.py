import argparse
import logging
import os
import shutil
from pathlib import Path
from typing import List
import nbconvert
import yaml
from traitlets.config import Config

logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def add_badges(notebook_path: str, is_local: bool) -> str:
    if is_local:
        return ""
    repo_name = os.environ.get("GITHUB_REPOSITORY", "zenml-io/zenml")
    relative_path = os.path.relpath(notebook_path, start="tutorials")
    colab_badge = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{repo_name}/blob/main/tutorials/{relative_path})"
    local_badge = f"[![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/{repo_name})"
    return f"{colab_badge} {local_badge}\n\n"


def convert_notebook_to_markdown(
    notebook_path: str, output_dir: str, is_local: bool
) -> str:
    c = Config()
    c.MarkdownExporter.preprocessors = [
        "nbconvert.preprocessors.ExtractOutputPreprocessor"
    ]

    exporter = nbconvert.MarkdownExporter(config=c)
    output, _ = exporter.from_filename(notebook_path)

    badges = add_badges(notebook_path, is_local)
    output = badges + output

    output_filename = Path(notebook_path).stem + ".md"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    logger.info(f"Successfully converted {notebook_path} to {output_path}")
    return output_filename


def update_toc(toc_path: str, guide_type: str, converted_files: List[str]) -> None:
    with open(toc_path, 'r') as f:
        toc_lines = f.readlines()

    guide_section = f"## {guide_type}\n"
    guide_section_index = -1
    next_section_index = -1

    # Find the guide section and the next section
    for i, line in enumerate(toc_lines):
        if line.strip() == guide_section.strip():
            guide_section_index = i
        elif guide_section_index != -1 and line.startswith('##'):
            next_section_index = i
            break

    # If guide section not found, add it at the end
    if guide_section_index == -1:
        guide_section_index = len(toc_lines)
        toc_lines.append('\n' + guide_section)

    # Create new lines for the guide
    new_lines = [guide_section]
    for file in converted_files:
        file_name = os.path.splitext(file)[0]
        new_lines.append(f"* [{file_name.replace('-', ' ').title()}](user-guide/{guide_type.lower().replace(' ', '-')}/{file_name}.md)\n")

    # Replace or insert the new lines
    if next_section_index != -1:
        toc_lines[guide_section_index:next_section_index] = new_lines
    else:
        toc_lines[guide_section_index:] = new_lines + ['\n']

    # Write the updated TOC
    with open(toc_path, 'w') as f:
        f.writelines(toc_lines)

    logger.info(f"Successfully updated TOC at {toc_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Update GitBook content from Jupyter notebooks."
    )
    parser.add_argument(
        "--guide-type",
        type=str,
        default="Starter guide",
        help="Type of guide to process",
    )
    parser.add_argument(
        "--local", action="store_true", help="Run in local mode (skips adding badges)"
    )
    args = parser.parse_args()

    notebook_dir = Path(f'tutorials/{args.guide_type.lower().replace(" ", "-")}')
    output_dir = Path(
        f'docs/book/user-guide/{args.guide_type.lower().replace(" ", "-")}'
    )
    logger.info(f"Converting notebooks from {notebook_dir} to {output_dir}")
    toc_path = Path("docs/book/toc.md")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converted_files = []
    for notebook_path in sorted(notebook_dir.glob("*.ipynb")):
        output_filename = convert_notebook_to_markdown(
            str(notebook_path), str(output_dir), args.local
        )
        if output_filename:
            converted_files.append(output_filename)

    if not converted_files:
        raise ValueError(f"No files were converted for {args.guide_type}")

    update_toc(str(toc_path), args.guide_type, converted_files)


if __name__ == "__main__":
    main()
