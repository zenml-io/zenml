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
"""Tests for the Llama Index Document Materializer."""

from tests.unit.test_general import _test_materializer


def test_llama_index_document_materializer(clean_client):
    """Tests whether the steps work for the Llama Index Document materializer."""
    from langchain.docstore.document import Document as LCDocument
    from llama_index.core import Document
    from llama_index.core.schema import ObjectType

    from zenml.integrations.llama_index.materializers.document_materializer import (
        LlamaIndexDocumentMaterializer,
    )

    page_content = (
        "Axl, Aria and Blupus were very cold during the winter months."
    )
    document = _test_materializer(
        step_output=Document(text=page_content),
        materializer_class=LlamaIndexDocumentMaterializer,
        expected_metadata_size=2,
    )

    assert document.get_type() == ObjectType.DOCUMENT
    assert document.text == page_content
    assert isinstance(document.to_langchain_format(), LCDocument)
