import argparse
import os
import subprocess
from pathlib import Path
from typing import List, Optional

PYDOCSTYLE_CMD = (
    "pydocstyle --convention=google --add-ignore=D100,D101,D102,"
    "D103,D104,D105,D107,D202"
)

API_DOCS_TITLE = "# Welcome to the ZenML Api Docs\n"
INTEGRATION_DOCS_TITLE = "# Welcome to the ZenML Integration Docs\n"

API_DOCS = "core_code_docs"
INTEGRATION_DOCS = "integration_code_docs"


def to_md_file(
    markdown_str: str,
    filename: str,
    out_path: Path = Path("."),
) -> None:
    """Creates an API docs file from a provided text.

    Args:
        markdown_str (str): Markdown string with line breaks to write to file.
        filename (str): Filename without the .md
        out_path (str): The output directory
    """
    if not markdown_str:
        # Don't write empty files
        return

    md_file = filename
    if not filename.endswith(".md"):
        md_file = filename + ".md"

    print(f"Writing {md_file}.")
    with open(os.path.join(out_path, md_file), "w", encoding="utf-8") as f:
        f.write(markdown_str)


def _is_module_ignored(module_name: str, ignored_modules: List[str]) -> bool:
    """Checks if a given module is ignored."""
    if module_name.split(".")[-1].startswith("_"):
        return True

    for ignored_module in ignored_modules:
        if module_name == ignored_module:
            return True

        # Check is module is subpackage of an ignored package
        if module_name.startswith(ignored_module + "."):
            return True

    return False


def generate_title(s: str) -> str:
    """Remove underscores and capitalize first letter to each word."""
    s = s.replace("_", " ")
    s = s.title()
    return s


def create_entity_docs(
    api_doc_file_dir: Path,
    ignored_modules: List[str],
    sources_path: Path,
    index_file_contents: Optional[List[str]],
    md_prefix: Optional[str],
) -> Optional[List[str]]:
    """Create structure for mkdocs with separate md files for each top level
    entity.

    Args:
        api_doc_file_dir: Directory in which to save the api/docs
        ignored_modules: List of entities to ignore
        sources_path: Path to the zenml src directory
        index_file_contents: Contents of the index file to append to
        md_prefix: Prefix that will help distinguish between the pages

    """
    for item in sources_path.iterdir():
        if item.name not in ignored_modules:
            is_python_file = item.is_file() and item.name.endswith(".py")
            is_non_empty_dir = item.is_dir() and any(item.iterdir())

            if is_python_file or is_non_empty_dir:
                item_name = generate_title(item.stem)

                # Extract zenml import path from sources path
                # Example: src/zenml/cli/function.py ->  zenml.cli
                zenml_import_path = ".".join(item.parts[1:-1])

                module_md = (
                    f"# {item_name}\n\n"
                    f"::: {zenml_import_path}.{item.stem}\n"
                    f"    handler: python\n"
                    f"    rendering:\n"
                    f"      show_root_heading: true\n"
                    f"      show_source: true\n"
                )

                if md_prefix:
                    file_name = md_prefix + "-" + item.stem
                else:
                    file_name = item.stem
                to_md_file(
                    module_md,
                    file_name,
                    out_path=api_doc_file_dir,
                )

                if index_file_contents:
                    index_entry = (
                        f"# [{item_name}]"
                        f"({API_DOCS}/{md_prefix}-{item.stem})\n\n"
                        f"::: {zenml_import_path}.{item.stem}\n"
                        f"    handler: python\n"
                        f"    selection:\n"
                        f"        members: false\n"
                    )

                    index_file_contents.append(index_entry)

    return index_file_contents


def create_cli_docs(
    cli_dev_doc_file_dir: Path,
    ignored_modules: List[str],
    sources_path: Path,
) -> None:
    # TODO [MEDIUM]: Find Solution for issue with click-decorated functions
    #  Some resources concerning this issue can be found here
    #  https://github.com/mkdocstrings/mkdocstrings/issues/162
    #  https://mkdocstrings.github.io/troubleshooting/#my-wrapped-function-shows-documentationcode-for-its-wrapper-instead-of-its-own
    create_entity_docs(
        api_doc_file_dir=cli_dev_doc_file_dir,
        ignored_modules=ignored_modules,
        sources_path=sources_path,
        index_file_contents=None,
        md_prefix="cli",
    )


def generate_docs(
    path: Path,
    output_path: Path,
    ignored_modules: Optional[List[str]] = None,
    validate: bool = False,
) -> None:
    """Generates top level separation of primary entities inside th zenml source
    directory for the purpose of generating mkdocstring markdown files.

    Args:
        path: Selected paths or import name for markdown generation.
        output_path: The output path for the creation of the markdown files.
        ignored_modules: A list of modules that should be ignored.
        validate: Boolean if pydocstyle should be verified within dir
    """
    # Set up output paths for the generated md files
    api_doc_file_dir = output_path / API_DOCS
    cli_dev_doc_file_dir = output_path / API_DOCS / "cli"
    client_dev_doc_file_dir = output_path / API_DOCS / "client"
    integrations_dev_doc_file_dir = output_path / INTEGRATION_DOCS

    api_doc_file_dir.mkdir(parents=True, exist_ok=True)
    cli_dev_doc_file_dir.mkdir(parents=True, exist_ok=True)
    client_dev_doc_file_dir.mkdir(parents=True, exist_ok=True)
    integrations_dev_doc_file_dir.mkdir(parents=True, exist_ok=True)

    if not ignored_modules:
        ignored_modules = list()

    # The Cli docs are treated differently as the user facing docs need to be
    # split from the developer-facing docs
    ignored_modules.append("cli")
    ignored_modules.append("client")
    ignored_modules.append("integrations")
    # Validate that all docstrings conform to pydocstyle rules
    if (
        validate
        and Path(path).is_dir()
        and subprocess.call(f"{PYDOCSTYLE_CMD} {path}", shell=True) > 0
    ):
        raise Exception(f"Validation for {path} failed.")

    index_file_contents = [API_DOCS_TITLE]

    index_file_contents = create_entity_docs(
        api_doc_file_dir=api_doc_file_dir,
        ignored_modules=ignored_modules,
        sources_path=path,
        index_file_contents=index_file_contents,
        md_prefix="core",
    )

    index_file_str = "\n".join(sorted(index_file_contents))
    to_md_file(
        index_file_str,
        "index.md",
        out_path=output_path,
    )

    integration_file_contents = [INTEGRATION_DOCS_TITLE]
    create_entity_docs(
        api_doc_file_dir=integrations_dev_doc_file_dir,
        ignored_modules=["__init__.py", "__pycache__"],
        sources_path=path / "integrations",
        index_file_contents=integration_file_contents,
        md_prefix="integrations",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Arguments to run the" "mkdocstrings helper"
    )
    # Required positional argument
    parser.add_argument(
        "--path",
        type=str,
        default="src/zenml",
        help="Location of the source code",
    )

    # Optional positional argument
    parser.add_argument(
        "--output_path",
        type=str,
        default="docs/mkdocs",
        help="Location at which to generate the markdown file",
    )

    # Optional argument
    parser.add_argument(
        "--ignored_modules",
        type=List[str],
        default=["VERSION", "README.md", "__init__.py", "__pycache__"],
        help="Top level entities that should not end up in "
        "the api docs (e.g. README.md, __init__",
    )

    # Switch
    parser.add_argument(
        "--validate", action="store_true", help="A boolean switch"
    )

    args = parser.parse_args()
    print(args.validate)

    generate_docs(
        path=Path(args.path),
        output_path=Path(args.output_path),
        ignored_modules=args.ignored_modules,
        validate=args.validate,
    )
