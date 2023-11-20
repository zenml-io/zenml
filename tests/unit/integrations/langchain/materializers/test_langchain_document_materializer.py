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


from tests.unit.test_general import _test_materializer


def test_langchain_document_materializer(clean_workspace):
    """Tests whether the steps work for the Langchain Document materializer."""
    from zenml.integrations.langchain.materializers.document_materializer import (
        LangchainDocumentMaterializer,
    )

    page_content = (
        "Axl, Aria and Blupus had a wonderful summer holiday together."
    )
    from langchain.docstore.document import Document

    langchain_document = _test_materializer(
        step_output=Document(page_content=page_content),
        materializer_class=LangchainDocumentMaterializer,
        expected_metadata_size=2,
    )

    assert langchain_document.page_content == page_content
