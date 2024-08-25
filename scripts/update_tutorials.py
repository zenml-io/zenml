"""Script to update GitBook content from Jupyter notebooks."""

import argparse
import filecmp
import logging
import os
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

import nbconvert
from traitlets.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_badges(notebook_path: Path, is_local: bool) -> str:
    """Add Colab and Local badges to the notebook if not running locally.

    Args:
        notebook_path (Path): Path to the notebook file.
        is_local (bool): Flag indicating if running locally.

    Returns:
        str: Badge markdown or empty string if local.
    """
    if is_local:
        return ""
    repo_name = os.environ.get("GITHUB_REPOSITORY", "zenml-io/zenml")
    relative_path = notebook_path.relative_to("tutorials")
    colab_badge = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{repo_name}/blob/main/tutorials/{relative_path})"
    local_badge = f"[![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/{repo_name}/blob/main/tutorials/{relative_path})"
    return f"{colab_badge} {local_badge}\n\n"


def convert_notebook_to_markdown(
    notebook_path: Path, output_dir: Path, is_local: bool
) -> str:
    """Convert Jupyter notebook to Markdown and add badges if not local.

    Args:
        notebook_path (Path): Path to the input notebook.
        output_dir (Path): Directory to save the output Markdown file.
        is_local (bool): Flag to determine if running locally.

    Returns:
        str: Name of the output Markdown file.
    """
    c = Config()
    c.MarkdownExporter.preprocessors = [
        "nbconvert.preprocessors.ExtractOutputPreprocessor"
    ]

    exporter = nbconvert.MarkdownExporter(config=c)
    output, _ = exporter.from_filename(str(notebook_path))

    # Define the base directory for the user guide
    user_guide_base = Path("docs/book/user-guide")

    # Calculate the relative path from the notebook to the tutorials directory
    relative_to_tutorials = notebook_path.relative_to(Path("tutorials"))

    # Calculate the expected final path of the markdown file
    expected_markdown_path = user_guide_base / relative_to_tutorials.parent

    # Define the location of the .gitbook/assets directory
    gitbook_assets = Path("docs/book/.gitbook/assets")

    # Calculate the relative path from the expected markdown location to the .gitbook/assets directory
    relative_path = os.path.relpath(gitbook_assets, expected_markdown_path)

    # Adjust image paths
    def replace_path(match):
        old_path = match.group(1)
        image_name = Path(old_path).name
        new_path = str(Path(relative_path) / image_name)
        return f"]({new_path}"

    output = re.sub(r"\]\((.*?\.gitbook/assets/[^)]+)", replace_path, output)

    badges = add_badges(notebook_path, is_local)
    output = badges + output

    output_filename = notebook_path.stem + ".md"
    output_path = output_dir / output_filename

    output_path.write_text(output, encoding="utf-8")

    logger.info(f"Successfully converted {notebook_path} to {output_path}")
    return output_filename


def generate_suggested_toc(guide_type: str, converted_files: List[str]) -> str:
    """Generate a suggested table of contents for a guide.

    Args:
        guide_type (str): The type of guide.
        converted_files (List[str]): List of converted markdown files.

    Returns:
        str: Suggested table of contents as a string.
    """
    toc = f"## {guide_type}\n\n"
    toc += f"* [🐣 {guide_type}](user-guide/{guide_type.lower().replace(' ', '-')}/README.md)\n"

    # Sort files to ensure consistent ordering
    sorted_files = sorted(converted_files)

    # Keep track of the current directory level
    current_level = 0

    for file in sorted_files:
        if file != "README.md":
            path_parts = Path(file).parts
            file_name = Path(file).stem

            # Calculate the new level based on the number of subdirectories
            new_level = len(path_parts) - 1

            # Adjust indentation based on directory level
            while current_level < new_level:
                toc += (
                    "  " * (current_level + 1)
                    + "* "
                    + path_parts[current_level].capitalize()
                    + "\n"
                )
                current_level += 1
            while current_level > new_level:
                current_level -= 1

            title = " ".join(
                word.capitalize() for word in file_name.split("_")[1:]
            )
            toc += (
                "  " * (current_level + 1)
                + f"* [{title}](user-guide/{guide_type.lower().replace(' ', '-')}/{file})\n"
            )

    return toc


def process_tutorials(is_local: bool) -> Dict[str, Tuple[str, List[str]]]:
    """Process all tutorial directories by converting notebooks to markdown and updating the table of contents.

    Args:
        is_local (bool): Flag indicating if running locally.

    Returns:
        Dict[str, Tuple[str, List[str]]]: Dictionary with guide names as keys and tuples of
        (suggested table of contents, and retained files) as values.
    """
    tutorials_dir = Path("tutorials")
    results = {}

    for guide_dir in tutorials_dir.iterdir():
        if not guide_dir.is_dir():
            continue

        guide_type = guide_dir.name.replace("-", " ").title()
        output_base_dir = Path("docs") / "book" / "user-guide" / guide_dir.name
        temp_dir = Path(tempfile.mkdtemp())

        converted_files = []
        updated_files = []

        # Use rglob to find all .ipynb files, including in subdirectories
        for notebook_path in sorted(guide_dir.rglob("*.ipynb")):
            # Calculate the relative path within the guide directory
            relative_path = notebook_path.relative_to(guide_dir)

            # Create corresponding subdirectories in temp_dir and output_dir
            temp_output_dir = temp_dir / relative_path.parent
            final_output_dir = output_base_dir / relative_path.parent
            temp_output_dir.mkdir(parents=True, exist_ok=True)
            final_output_dir.mkdir(parents=True, exist_ok=True)

            output_filename = convert_notebook_to_markdown(
                notebook_path, temp_output_dir, is_local
            )
            converted_files.append(str(relative_path.parent / output_filename))

            # Check if the file is new or has been modified
            output_path = final_output_dir / output_filename
            if not output_path.exists() or not filecmp.cmp(
                temp_output_dir / output_filename, output_path
            ):
                updated_files.append(
                    str(relative_path.parent / output_filename)
                )

        if not converted_files:
            logger.warning(f"No files were converted for {guide_type}")
            continue

        existing_files = (
            [
                str(f.relative_to(output_base_dir))
                for f in output_base_dir.rglob("*.md")
            ]
            if output_base_dir.exists()
            else []
        )
        retained_files = existing_files

        suggested_toc = generate_suggested_toc(guide_type, converted_files)

        # Update only the changed files
        for file in updated_files:
            source = temp_dir / file
            destination = output_base_dir / file
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, destination)
            if file not in existing_files:
                retained_files.append(file)

        shutil.rmtree(temp_dir)

        results[guide_type] = (suggested_toc, retained_files)

    return results


def main():
    """Main function to update the GitBook content from Jupyter notebooks."""
    parser = argparse.ArgumentParser(
        description="Update GitBook content from Jupyter notebooks."
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run in local mode (skips adding badges)",
    )
    args = parser.parse_args()

    try:
        logger.info("Starting to process tutorials...")
        results = process_tutorials(args.local)

        for guide_type, (suggested_toc, retained_files) in results.items():
            safe_guide_type = guide_type.lower().replace(" ", "_")
            print(f"suggested_toc_{safe_guide_type}<<EOF")
            print(suggested_toc)
            print("EOF")
            print(f"retained_files_{safe_guide_type}={','.join(retained_files) if retained_files else ''}")

        logger.info("Tutorial processing completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.error(traceback.format_exc())
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()