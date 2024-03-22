#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Verify the current flavor implementations contains valid fields."""

import os.path
import tempfile
from typing import Type

import click
import requests
from requests import Response
from rich.console import Console
from rich.progress import track

from zenml import __version__
from zenml.stack import Flavor
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.zen_stores.sql_zen_store import SqlZenStore


@click.group()
def cli() -> None:
    """CLI base command for the ZenML dev framework."""


@cli.group()
def flavors() -> None:
    """Interact with flavors in dev environment."""


@flavors.group()
def verify() -> None:
    """Verify urls on flavors."""


@verify.command(
    "docs",
    help="Verify that all flavor doc urls are valid. "
    "Whenever new flavors are added or when the structure of the docs is "
    "adjusted, there is potential to break the link between flavors and "
    "their corresponding docs."
    "\n"
    "The `flavor_docs_url` property on flavors is built with a very "
    "specific assumption of how this url is built. This script is "
    "designed to validate that this assumption still holds. But there are "
    "some manual steps involved:"
    "\n"
    "1) Push your code."
    "\n"
    "2) Use the GitBook UI to provision a Test Space with an unlisted"
    " public url that uses your code."
    "\n"
    "3) Set the RootDomain of this unlisted gitbook space as "
    "parameter for this command."
    "\n"
    "4) Run this command to make sure all the urls mentioned in code are "
    "working.",
)
@click.option(
    "-r",
    "--root-domain",
    "root_domain",
    type=str,
    required=False,
    default=f"https://docs.zenml.io/v/{__version__}",
)
@click.option(
    "-i",
    "--ignore-passing",
    "ignore_passing",
    help="If True, only print failing urls.",
    is_flag=True,
    type=click.BOOL,
    default=True,
)
def docs(root_domain: str, ignore_passing: bool) -> None:
    fr = FlavorRegistry()
    flavors = fr.builtin_flavors + fr.integration_flavors

    for flavor in track(flavors, description="Analyzing ..."):
        url_components = flavor().docs_url.split("/component-gallery", 1)
        url_components[0] = root_domain

        url = url_components[0] + "/component-gallery" + url_components[1]

        r = requests.head(url)
        if r.status_code == 404:
            style = "bold red"
            text = (
                f"{flavor().__module__}, flavor_docs_url points at {url} "
                f"which does not seem to exist."
            )

            Console().print(text, style=style)
        elif not ignore_passing:
            style = "green"

            text = (
                f"The url for {flavor().__module__} points to a valid "
                f"location: {url}"
            )

            Console().print(text, style=style)

    for flavor in track(flavors, description="Analyzing sdk_docs..."):
        url = flavor().sdk_docs_url

        r = requests.head(url)
        if r.status_code == 404:
            style = "bold red"
            text = (
                f"{flavor().__module__}, sdk_docs_url points at {url} "
                f"which does not seem to exist."
            )

            Console().print(text, style=style)
        elif not ignore_passing:
            style = "green"

            text = (
                f"The url for {flavor().__module__} points to a valid "
                f"location: {url}"
            )

            Console().print(text, style=style)


@verify.command(
    "logos",
    help="Verify that all flavor logo urls are valid images. "
    "The logos for all flavors are hosted in an s3 bucket that is "
    "publicly accessible."
    "\n"
    "The `logo_urls` are defined as a property on all flavors. When "
    "creating new flavors or when making changes to the s3 bucket"
    "structure, it might be necessary to verify that all flavors are "
    "still pointing at valid images.",
)
@click.option(
    "-i",
    "--ignore-passing",
    "ignore_passing",
    help="If True, only print failing urls.",
    is_flag=True,
    type=click.BOOL,
    default=True,
)
def logos(ignore_passing: bool) -> None:
    fr = FlavorRegistry()
    flavors = fr.builtin_flavors + fr.integration_flavors

    for flavor in track(flavors, description="Analyzing ..."):
        url = flavor().logo_url

        r = requests.get(url)
        if r.status_code == 404:
            style = "bold red"
            text = (
                f"{flavor().__module__}, logo_url points at {url} "
                f"which does not seem to exist."
            )
            Console().print(text, style=style)

        _verify_image_not_corrupt(r, flavor)

        if not ignore_passing:
            style = "green"

            text = (
                f"The url for {flavor().__module__} points to a valid "
                f"location: {url}"
            )

            Console().print(text, style=style)


def _verify_image_not_corrupt(r: Response, flavor: Type[Flavor]):
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdirname:
        type_filepath = os.path.join(tmpdirname, flavor().type)
        if not os.path.exists(type_filepath):
            os.makedirs(type_filepath)

        filepath = os.path.join(
            type_filepath, flavor().logo_url.split("/")[-1]
        )
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        if not filepath.endswith("svg"):
            assert Image.open(filepath)  # Open image without failing
        else:
            pass  # Not yet verifying valid svg


@flavors.command(
    "sync",
    help="During development of new flavors, this function can be used to "
    "purge the database and sync all flavors, including the new one, "
    "into the database.",
)
def sync():
    from zenml.client import Client

    store = Client().zen_store
    if isinstance(store, SqlZenStore):
        store._sync_flavors()
    else:
        style = "bold orange"
        text = (
            "This command requires you to be connected to a SqlZenStore. "
            "Please disconnect from the RestZenStore and try again."
        )
        Console().print(text, style=style)
