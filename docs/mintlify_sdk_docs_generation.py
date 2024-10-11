import os
import argparse
import logging
import tempfile
from rich import print, inspect
from lazydocs_generation import generate_docs
import json

OUTPUT_FOLDER_SUBPATHS = ["core", "integrations"]
CLIENT_RELATIVE_PATH = "client.py"
INTEGRATIONS_RELATIVE_PATH = "integrations"
CLI_RELATIVE_PATH = "cli/__init__.py"
IGNORED_MODULES = ["pandas", "numpy"]


def create_output_folders(output_path: str) -> None:
    # Check if output_path exists and has contents
    if os.path.exists(output_path) and os.listdir(output_path):
        # Delete all contents of the output_path
        for item in os.listdir(output_path):
            item_path = os.path.join(output_path, item)
            if os.path.isdir(item_path):
                import shutil

                shutil.rmtree(item_path)

    # Create new output folders
    for subpath in OUTPUT_FOLDER_SUBPATHS:
        os.makedirs(os.path.join(output_path, subpath), exist_ok=True)


def generate_markdown_files(
    source_repo_path: str, output_path: str, code_links_base_url: str
) -> None:
    # INTEGRATIONS DOCS
    # first generate the base files for the integrations
    integrations_input_path = os.path.join(
        source_repo_path, INTEGRATIONS_RELATIVE_PATH
    )
    integrations_output_path = os.path.join(output_path, "integrations")
    print(f"Integrations input path: {integrations_input_path}")
    print(f"Integrations output path: {integrations_output_path}")
    generate_docs(
        paths=[integrations_input_path],
        output_path=integrations_output_path,
        src_root_path=source_repo_path,
        src_base_url=code_links_base_url,
        watermark=False,
        ignored_modules=IGNORED_MODULES,
        output_format="mdx",
    )

    # recursively iterate through all the files just created in the output_path
    # and replace `<!-- markdownlint-disable -->` with ""
    for root, dirs, files in os.walk(integrations_output_path):
        for file in files:
            if file.endswith(".mdx"):
                with open(os.path.join(root, file), "r") as f:
                    content = f.read()
                    content = content.replace("<!-- markdownlint-disable -->", "")
                with open(os.path.join(root, file), "w") as f:
                    f.write(content)

    # iterate through the submodules
    for submodule in os.listdir(
        os.path.join(source_repo_path, INTEGRATIONS_RELATIVE_PATH)
    ):
        submodule_path = os.path.join(
            source_repo_path, INTEGRATIONS_RELATIVE_PATH, submodule
        )
        if os.path.isdir(submodule_path):
            # Create a temporary folder for this submodule
            with tempfile.TemporaryDirectory() as temp_dir:
                # Get all the paths of the .py files in the submodule
                py_files = []
                for root, dirs, files in os.walk(submodule_path):
                    py_files.extend(
                        os.path.join(root, file)
                        for file in files
                        if file.endswith(".py") and file != "__init__.py"
                    )
                # Generate docs for all .py files in the submodule
                generate_docs(
                    paths=py_files,
                    output_path=temp_dir,
                    src_root_path=source_repo_path,
                    src_base_url=code_links_base_url,
                    watermark=False,
                    ignored_modules=IGNORED_MODULES,
                    output_format="mdx",
                )

                # Concatenate all mdx files in the temporary folder
                combined_content = ""
                for mdx_file in os.listdir(temp_dir):
                    if mdx_file.endswith(".mdx"):
                        with open(os.path.join(temp_dir, mdx_file), "r") as f:
                            combined_content += f.read() + "\n\n"

                # replace `<!-- markdownlint-disable -->` with "" inside the string
                combined_content = combined_content.replace(
                    "<!-- markdownlint-disable -->", ""
                )

                # Append the combined content to the existing .md file
                if combined_content:
                    md_file_path = os.path.join(
                        output_path, "integrations", f"{submodule}.mdx"
                    )
                    with open(md_file_path, "a") as md_file:
                        md_file.write(combined_content)


def update_mint_json(mint_json_location: str, output_files_path: str) -> None:
    # load the mint.json file as a dictionary
    with open(mint_json_location, "r") as f:
        mint_json = json.load(f)

    # get all the .mdx files in the output_files_path
    mdx_files = [f for f in os.listdir(os.path.join(output_files_path, "integrations")) if f.endswith(".mdx")]

    files_for_code_docs_group = sorted([
        "sdk/python-client",
        *[f"sdk/integrations/{mdx_file[:-4]}" for mdx_file in mdx_files],
    ])

    # Find the "📚 Code Docs" group in the navigation and update its pages
    for item in mint_json["navigation"]:
        if item.get("group") == "\ud83d\udcda Code Docs":
            item["pages"] = files_for_code_docs_group
            break
    else:
        # If the group doesn't exist, create it
        mint_json["navigation"].append(
            {"group": "\ud83d\udcda Code Docs", "pages": files_for_code_docs_group}
        )

    # write the updated mint.json file
    with open(mint_json_location, "w") as f:
        json.dump(mint_json, f, indent=4)


def main(
    source_repo_path: str,
    output_path: str,
    code_links_base_url: str,
    mint_json_path: str,
) -> None:
    """Generate Mintlify SDK documentation.

    Args:
        source_repo_path (str): Path to the source repository.
        output_path (str): Path to output the generated documentation.
        code_links_base_url (str): Base URL for code links.
        mint_json_location (str): Location of the mint.json file.

    Returns:
        None
    """

    print(f"Source repo path: {os.path.abspath(source_repo_path)}")
    print(f"Output path: {os.path.abspath(output_path)}")
    print(f"Code links base URL: {code_links_base_url}")
    print(f"mint.json location: {mint_json_path}")

    create_output_folders(output_path)
    generate_markdown_files(source_repo_path, output_path, code_links_base_url)
    update_mint_json(mint_json_path, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Mintlify SDK documentation"
    )
    parser.add_argument(
        "--source_repo_path",
        default="src/zenml",
        help="Path to the source repository",
    )
    parser.add_argument(
        "--output_path",
        default="docs/mintlify/sdk",
        help="Path to output the generated documentation",
    )
    parser.add_argument(
        "--code_links_base_url",
        default="https://github.com/zenml-io/zenml/tree/main/src/zenml",
        help="Base URL for code links",
    )
    parser.add_argument(
        "--mint_json_location",
        default="docs/mintlify/mint.json",
        help="Location of the mint.json file",
    )

    args = parser.parse_args()

    main(
        args.source_repo_path,
        args.output_path,
        args.code_links_base_url,
        args.mint_json_location,
    )
