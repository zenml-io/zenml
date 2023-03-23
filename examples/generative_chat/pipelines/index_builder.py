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


from steps.docs_loader import DocsLoaderParameters, docs_loader
from steps.index_generator import IndexGeneratorParameters, index_generator
from steps.slack_loader import SlackLoaderParameters, slack_loader
from steps.utils import SLACK_CHANNEL_IDS, get_release_date, page_exists

from zenml.pipelines import pipeline


@pipeline()
def docs_to_index_pipeline(document_loader, slack_loader, index_generator):
    documents = document_loader()
    slack_docs = slack_loader()
    index_generator(documents, slack_docs)


zenml_version = "0.36.0"
base_url = "https://docs.zenml.io"
docs_url = f"https://docs.zenml.io/v/{zenml_version}/"

if not page_exists(docs_url):
    print(f"Couldn't find docs page for zenml version '{zenml_version}'.")

release_date, next_release_date = get_release_date("zenml", zenml_version)

docs_to_index_pipeline = docs_to_index_pipeline(
    document_loader=docs_loader(
        params=DocsLoaderParameters(docs_uri=docs_url, base_url=base_url)
    ),
    index_generator=index_generator(params=IndexGeneratorParameters()),
    slack_loader=slack_loader(
        params=SlackLoaderParameters(
            channel_ids=SLACK_CHANNEL_IDS,
            earliest_date=release_date,
            latest_date=next_release_date,
        )
    ),
)

try:
    docs_to_index_pipeline.run()
except Exception as e:
    print(f"Failed to build index for zenml version '{zenml_version}'.")
    print(e)
