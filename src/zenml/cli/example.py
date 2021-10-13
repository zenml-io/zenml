#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

# TODO [MEDIUM]: Add logic via direct GitHub repo pulling

# import os
# from typing import List
#
# import click
#
# from zenml.cli.cli import cli
# from zenml.utils import path_utils
#
#
# def get_examples_dir() -> str:
#     """Return the examples dir."""
#     cli_dir = os.path.dirname(__file__)
#     package_dir = os.path.dirname(os.path.dirname(cli_dir))
#     examples_dir = os.path.join(package_dir, "examples")
#     return examples_dir
#
#
# def get_all_examples() -> List[str]:
#     """Get all the examples"""
#     examples = []
#     for name in sorted(os.listdir(get_examples_dir())):
#         # Skip hidden files (like .gitignore)
#         if (
#             not name.startswith(".")
#             and not name.startswith("__")
#             and not name.startswith("README")
#         ):
#             examples.append(name)
#     return examples
#
#
# def get_example_readme(example_path) -> str:
#     """Get the example README file contents."""
#     with open(os.path.join(example_path, "README.md")) as readme:
#         readme_content = readme.read()
#     return readme_content
#
#
# @cli.group(help="Access all ZenML examples.")
# def example():
#     """Examples group"""
#
#
# @example.command(help="List the available examples.")
# def list():
#     """List all available examples."""
#     click.echo("Listing examples: \n")
#     for name in get_all_examples():
#         click.echo(f"{name}")
#     click.echo("\nTo pull the examples, type: ")
#     click.echo("zenml example pull EXAMPLE_NAME")
#
#
# @example.command(help="Find out more about an example.")
# @click.argument("example_name")
# def info(example_name):
#     """Find out more about an example."""
#     example_dir = os.path.join(get_examples_dir(), example_name)
#     readme_content = get_example_readme(example_dir)
#     click.echo(readme_content)
#
#
# @example.command(
#     help="Pull examples straight " "into your current working directory."
# )
# @click.argument("example_name", required=False, default=None)
# def pull(example_name):
#     """Pull examples straight " "into your current working directory."""
#     examples_dir = get_examples_dir()
#     if not example_name:
#         examples = get_all_examples()
#     else:
#         examples = [example_name]
#
#     # Create destination dir.
#     dst = os.path.join(os.getcwd(), "zenml_examples")
#     path_utils.create_dir_if_not_exists(dst)
#
#     # Pull specified examples.
#     for example in examples:
#         dst_dir = os.path.join(dst, example)
#         # Check if example has already been pulled before.
#         if path_utils.file_exists(dst_dir):
#             if click.confirm(
#                 f"Example {example} is already pulled. "
#                 f"Do you wish to overwrite the directory?"
#             ):
#                 path_utils.rm_dir(dst_dir)
#             else:
#                 continue
#         click.echo(f"Pulling example {example}")
#         src_dir = os.path.join(examples_dir, example)
#         path_utils.copy_dir(src_dir, dst_dir)
#
#         click.echo(f"Example pulled in directory: {dst_dir}")
#
#     click.echo()
#     click.echo(
#         "Please read the README.md file in the respective example "
#         "directory to find out more about the example"
#     )
