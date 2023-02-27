import fileinput
import os
from distutils.dir_util import copy_tree
from typing import List

import click

from zenml.logger import get_logger
from zenml.utils.yaml_utils import load_yaml, write_yaml

logger = get_logger(__name__)


def replace_static_integration_imports(old_module: str, destination_src: str):
    """Replace all `zenml.integration.<integration_name>` with relative imports.

    `fileinput` moves the file and redirects stdout to write into it again, see
    https://stackoverflow.com/questions/39086/search-and-replace-a-line-in-a-file-in-python
    """
    integration_requirements = set()
    for root, _, files in os.walk(destination_src):
        rel_root = os.path.relpath(root, destination_src)
        num_dots = len(rel_root.split(os.sep)) + 1
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                for line in fileinput.input(file_path, inplace=True):
                    if old_module in line:
                        line = line.replace(old_module, "." * num_dots)
                    elif "zenml.integrations." in line:
                        required_integration = line.split(
                            "zenml.integrations."
                        )[1].split(".")[0]
                        integration_requirements.add(required_integration)
                    print(line, end="")  # writes into the file


def process_config(config_path: str, destination: str) -> List[str]:
    """Processes all components listed in the config content field.

    For each component, we extract the source path.
    If examples or docs are present, we also copy those to the destination path.
    """
    config = load_yaml(config_path)
    if "name" not in config:
        raise ValueError("Config must contain 'name' key.")
    integration_name = config["name"]

    components = config.get("content", [])
    component_sources = []
    for component_type, component_list in components.items():
        for component in component_list:
            if "src" not in component:
                raise ValueError(
                    f"Content[{component_type}[{component}]] must have 'src' "
                    "key."
                )
            component_sources.append(component["src"])

            if "example" in component:
                example = component["example"]
                destination_examples = os.path.join(destination, "examples")
                copy_tree(example, destination_examples)

            if "readme" in component:
                readme = component["readme"]
                destination_docs = os.path.join(destination, "docs")
                copy_tree(readme, destination_docs)

    destination_config = os.path.join(destination, "config.yaml")
    write_yaml(destination_config, config)

    return integration_name, component_sources


def get_license():
    return """
#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""


def write_integration_init(
    integration_src_root: str, component_sources: List[str]
):

    integration_init = os.path.join(integration_src_root, "__init__.py")
    with open(integration_init, "w") as f:

        # write license
        f.write(get_license)
        f.write("\n")

        # write import statements for all components
        variables = []
        for component_source in component_sources:
            parts = component_source.split(".")
            module = ".".join(parts[:-1])
            module = module.replace("src", "")
            variable = parts[-1]
            f.write(f"from {module} import {variable}\n")
            variables.append(variable)
        f.write("\n")

        # write `__all__` export for all components
        f.write("__all__ = [\n")
        for variable in variables:
            f.write(f'    "{variable}"\n')
        f.write("]\n")


@click.command()
@click.argument("config_path", type=click.STRING)
@click.argument("destination", type=click.STRING)
def main(config_path: str, destination: str):
    # Create destination folder if not present
    if not os.path.exists(destination):
        os.makedirs(destination)

    # Load and process config
    integration_name, component_sources = process_config(
        config_path, destination
    )

    # Copy integration source to `destination.src`
    integration_src = "src/zenml/integrations/" + integration_name
    destination_src = os.path.join(destination, "src")
    copy_tree(integration_src, destination_src)

    # Replace static imports
    old_module = f"zenml.integrations.{integration_name}"
    replace_static_integration_imports(old_module, destination_src)

    # Create main README linking to docs - TODO
    readme_path = os.path.join(destination, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# {integration_name}\n")
        f.write(
            f"See [docs]({integration_name}/README.md) for more information."
        )

    # Extract all requirements from integration class
    destination_requirements = os.path.join(destination, "requirements.txt")
    integration_class = ...  # TODO
    if integration_class.name != integration_name:
        logger.warning(
            f"Integration name in config ({integration_name}) does not match "
            f"integration class name ({integration_class.name})."
        )
    with open(destination_requirements, "w") as f:
        for requirement in integration_class.REQUIREMENTS:
            f.write(requirement + "\n")

    # override main __init__.py
    write_integration_init(
        integration_src_root=destination_src,
        component_sources=component_sources,  # TODO: this needs to come from the new config.yaml
    )

    # TODO: replace all internal links in copied docs

    # (copy unit tests into hub.tests.unit)

    # (copy integration tests into hub.tests.integration)


if __name__ == "__main__":
    main()
