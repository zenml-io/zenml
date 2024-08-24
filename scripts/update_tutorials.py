import argparse
import os
import shutil
from pathlib import Path
import nbconvert
from traitlets.config import Config
import tempfile
from typing import List, Tuple, Dict
import logging
import filecmp

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
    repo_name = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo_name:
        raise ValueError("GITHUB_REPOSITORY environment variable is not set")
    relative_path = notebook_path.relative_to("tutorials")
    colab_badge = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{repo_name}/blob/main/tutorials/{relative_path})"
    local_badge = f"[![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/{repo_name})"
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
    for file in sorted(converted_files):
        if file != "README.md":
            file_name = Path(file).stem
            title = " ".join(
                word.capitalize() for word in file_name.split("_")[1:]
            )
            toc += f"  * [{title}](user-guide/{guide_type.lower().replace(' ', '-')}/{file_name}.md)\n"
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
        output_dir = Path("docs") / "book" / "user-guide" / guide_dir.name
        temp_dir = Path(tempfile.mkdtemp())

        converted_files = []
        updated_files = []
        for notebook_path in sorted(guide_dir.glob("*.ipynb")):
            output_filename = convert_notebook_to_markdown(notebook_path, temp_dir, is_local)
            converted_files.append(output_filename)
            
            # Check if the file is new or has been modified
            output_path = output_dir / output_filename
            if not output_path.exists() or not filecmp.cmp(temp_dir / output_filename, output_path):
                updated_files.append(output_filename)

        if not converted_files:
            logger.warning(f"No files were converted for {guide_type}")
            continue

        existing_files = [f.name for f in output_dir.glob("*.md")] if output_dir.exists() else []
        retained_files = existing_files

        suggested_toc = generate_suggested_toc(guide_type, converted_files)

        # Update only the changed files
        output_dir.mkdir(parents=True, exist_ok=True)
        for file in updated_files:
            shutil.copy(temp_dir / file, output_dir / file)
            if file not in existing_files:
                retained_files.append(file)

        shutil.rmtree(temp_dir)

        results[guide_type] = (suggested_toc, retained_files)

    return results


def main():
    """Main function to update the GitBook content from Jupyter notebooks."""
    parser = argparse.ArgumentParser(description="Update GitBook content from Jupyter notebooks.")
    parser.add_argument("--local", action="store_true", help="Run in local mode (skips adding badges)")
    args = parser.parse_args()

    try:
        results = process_tutorials(args.local)

        for guide_type, (suggested_toc, retained_files) in results.items():
            logger.info(f"Suggested TOC for {guide_type}:\n{suggested_toc}")
            logger.info(f"Retained files: {retained_files}")

        if os.environ.get("GITHUB_ACTIONS"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                for guide_type, (suggested_toc, retained_files) in results.items():
                    f.write(f"suggested_toc_{guide_type.lower().replace(' ', '_')}<<EOF\n{suggested_toc}\nEOF\n")
                    f.write(f"retained_files_{guide_type.lower().replace(' ', '_')}={','.join(retained_files) if retained_files else ''}\n")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::An error occurred: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
