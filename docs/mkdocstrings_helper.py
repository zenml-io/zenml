import argparse
import ast
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
import re

PYDOCSTYLE_CMD = (
    "pydocstyle --convention=google --add-ignore=D100,D101,D102,"
    "D103,D104,D105,D107,D202"
)


API_DOCS_TITLE = "# Welcome to the ZenML SDK Docs\n"

INTEGRATION_DOCS_TITLE = "# Welcome to the ZenML Integration Docs\n"

API_DOCS = "core_code_docs"
INTEGRATION_DOCS = "integration_code_docs"


def to_md_file(
    markdown_str: str,
    filename: str,
    out_path: Path = Path("."),
) -> None:
    """Creates an SDK docs file from a provided text.

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


def extract_field_description_from_code(code: str, field_name: str) -> Optional[str]:
    """Extract Field description from Python code using AST parsing."""
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == field_name and isinstance(node.value, ast.Call):
                    # Check if it's a Field call
                    if (isinstance(node.value.func, ast.Name) and node.value.func.id == "Field") or \
                       (isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "Field"):
                        
                        # Extract description from Field arguments
                        for keyword in node.value.keywords:
                            if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                                return keyword.value.value
    except:
        pass
    return None


def generate_docstring_attributes_from_fields(file_path: Path) -> None:
    """Generate docstring attributes section from Pydantic Field descriptions."""
    if not file_path.exists() or not file_path.name.endswith('.py'):
        return
        
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Skip if no Field imports or pydantic usage
        if 'from pydantic import' not in content and 'import pydantic' not in content:
            return
            
        # Parse the file to find classes with Field definitions
        tree = ast.parse(content)
        modified = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class has Field definitions
                field_descriptions = {}
                class_start_line = node.lineno
                
                # Find Field definitions in the class
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        if isinstance(item.value, ast.Call):
                            # Check if it's a Field call
                            if (isinstance(item.value.func, ast.Name) and item.value.func.id == "Field") or \
                               (isinstance(item.value.func, ast.Attribute) and item.value.func.attr == "Field"):
                                
                                # Extract description
                                for keyword in item.value.keywords:
                                    if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                                        field_descriptions[field_name] = keyword.value.value
                
                # If we found Field descriptions, update the docstring
                if field_descriptions:
                    lines = content.split('\n')
                    docstring_start, docstring_end = find_class_docstring_range(lines, class_start_line - 1)
                    
                    if docstring_start is not None and docstring_end is not None:
                        # Extract existing docstring
                        existing_docstring = '\n'.join(lines[docstring_start:docstring_end + 1])
                        
                        # Check if it already has Attributes section
                        if 'Attributes:' not in existing_docstring:
                            # Generate attributes section
                            attributes_section = generate_attributes_section(field_descriptions)
                            
                            # Insert before the closing triple quotes
                            if existing_docstring.strip().endswith('"""'):
                                # Multi-line docstring
                                new_docstring = existing_docstring.rstrip('"""').rstrip() + '\n\n' + attributes_section + '\n    """'
                            elif existing_docstring.strip().endswith("'''"):
                                # Multi-line docstring with single quotes
                                new_docstring = existing_docstring.rstrip("'''").rstrip() + '\n\n' + attributes_section + "\n    '''"
                            else:
                                continue
                                
                            lines[docstring_start:docstring_end + 1] = new_docstring.split('\n')
                            modified = True
        
        if modified:
            file_path.write_text('\n'.join(lines), encoding='utf-8')
            
    except Exception as e:
        print(f"Warning: Could not process {file_path}: {e}")


def find_class_docstring_range(lines: List[str], class_line: int) -> Tuple[Optional[int], Optional[int]]:
    """Find the start and end line numbers of a class docstring."""
    # Look for docstring starting after class definition
    for i in range(class_line + 1, min(class_line + 10, len(lines))):
        line = lines[i].strip()
        if line.startswith('"""') or line.startswith("'''"):
            quote_type = '"""' if line.startswith('"""') else "'''"
            start_line = i
            
            # Check if it's a single-line docstring
            if line.count(quote_type) >= 2:
                return start_line, start_line
                
            # Find the end of multi-line docstring
            for j in range(i + 1, len(lines)):
                if quote_type in lines[j]:
                    return start_line, j
    return None, None


def generate_attributes_section(field_descriptions: dict) -> str:
    """Generate an Attributes section from field descriptions."""
    attributes_lines = ["    Attributes:"]
    
    for field_name, description in field_descriptions.items():
        # Clean up description - remove extra whitespace and line breaks
        clean_description = ' '.join(description.split())
        attributes_lines.append(f"        {field_name}: {clean_description}")
    
    return '\n'.join(attributes_lines)


def process_pydantic_files_in_directory(directory: Path) -> None:
    """Process all Python files in a directory to generate docstring attributes."""
    if not directory.exists():
        return
        
    print(f"Processing Pydantic files in {directory}...")
    
    # Find all Python files recursively
    python_files = list(directory.rglob("*.py"))
    
    for file_path in python_files:
        # Skip __pycache__ directories and other non-source files
        if "__pycache__" in str(file_path) or file_path.name.startswith("_"):
            continue
            
        generate_docstring_attributes_from_fields(file_path)


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
                    f"    options:\n"
                    f"      show_root_heading: true\n"
                    f"      show_source: true\n"
                    f"      members: true\n"
                )

                if md_prefix:
                    file_name = f"{md_prefix}-{item.stem}.md"
                    index_link = f"{API_DOCS}/{md_prefix}-{item.stem}.md"
                else:
                    file_name = f"{item.stem}.md"
                    index_link = f"{API_DOCS}/{item.stem}.md"

                to_md_file(
                    module_md,
                    file_name,
                    out_path=api_doc_file_dir,
                )

                if index_file_contents:
                    index_entry = (
                        f"# [{item_name}]"
                        f"({index_link})\n\n"
                        f"::: {zenml_import_path}.{item.stem}\n"
                        f"    options:\n"
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
    # First, process all Pydantic files to generate docstring attributes
    process_pydantic_files_in_directory(path)
    # Set up output paths for the generated md files
    api_doc_file_dir = output_path / API_DOCS
    cli_dev_doc_file_dir = output_path / API_DOCS / "cli"
    integrations_dev_doc_file_dir = output_path / INTEGRATION_DOCS

    api_doc_file_dir.mkdir(parents=True, exist_ok=True)
    cli_dev_doc_file_dir.mkdir(parents=True, exist_ok=True)
    integrations_dev_doc_file_dir.mkdir(parents=True, exist_ok=True)

    if not ignored_modules:
        ignored_modules = list()

    # The Cli docs are treated differently as the user facing docs need to be
    # split from the developer-facing docs
    ignored_modules.append("cli")
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

    # Fix links in index file to point to index.md instead of just the directory
    fixed_index_contents = []
    for line in index_file_contents:
        fixed_index_contents.append(line)

    index_file_str = "\n".join(sorted(fixed_index_contents))
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
        description="Arguments to run themkdocstrings helper"
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
        "the sdk docs (e.g. README.md, __init__",
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
