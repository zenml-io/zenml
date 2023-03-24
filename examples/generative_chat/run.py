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
import argparse
import logging

from pipelines.index_builder import (
    docs_to_index_pipeline,
)
from steps.docs_loader import DocsLoaderParameters, docs_loader
from steps.index_generator import IndexGeneratorParameters, index_generator
from steps.slack_loader import SlackLoaderParameters, slack_loader
from steps.utils import get_channel_id_from_name, get_release_date, page_exists

docs_version = "0.35.0"
base_url = "https://docs.zenml.io"
docs_url = f"https://docs.zenml.io/v/{docs_version}/"
channel_names = ["general"]
channel_ids = [
    get_channel_id_from_name(channel_name) for channel_name in channel_names
]

if not page_exists(docs_url):
    print(f"Couldn't find docs page for zenml version '{docs_version}'.")

release_date, next_release_date = get_release_date("zenml", docs_version)

parser = argparse.ArgumentParser(
    description="Build ZenML documentation index."
)
parser.add_argument(
    "--docs_version",
    type=str,
    default=docs_version,
    help="Docs version number",
)
parser.add_argument(
    "--base_url",
    type=str,
    default=base_url,
    help="Base URL for documentation site",
)
parser.add_argument(
    "--docs_url",
    type=str,
    default=docs_url,
    help="URL for documentation site",
)
args = parser.parse_args()

docs_version = args.docs_version
base_url = args.base_url
docs_url = args.docs_url

docs_to_index_pipeline = docs_to_index_pipeline(
    document_loader=docs_loader(
        params=DocsLoaderParameters(docs_uri=docs_url, base_url=base_url)
    ),
    index_generator=index_generator(params=IndexGeneratorParameters()),
    slack_loader=slack_loader(
        params=SlackLoaderParameters(
            channel_ids=channel_ids,
            earliest_date=release_date,
            latest_date=next_release_date,
        )
    ),
)


def main():
    try:
        docs_to_index_pipeline.run()
    except Exception as e:
        print(f"Failed to build index for docs version '{docs_version}'.")
        print(e)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main()
