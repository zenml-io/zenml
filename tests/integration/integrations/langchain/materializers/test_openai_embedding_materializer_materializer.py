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


def test_langchain_openai_embedding_materializer(clean_client):
    """Tests the Langchain OpenAI Embeddings materializer."""
    from langchain_community.embeddings import OpenAIEmbeddings

    from zenml.integrations.langchain.materializers.openai_embedding_materializer import (
        LangchainOpenaiEmbeddingMaterializer,
    )

    fake_key = "aria_and_blupus"
    fake_chunk_size = 1234

    original_embeddings = OpenAIEmbeddings(
        chunk_size=fake_chunk_size,
        openai_api_key=fake_key,
    )

    embeddings = _test_materializer(
        step_output=original_embeddings,
        materializer_class=LangchainOpenaiEmbeddingMaterializer,
        expected_metadata_size=1,
    )

    # Test that essential configuration is preserved
    assert isinstance(embeddings, OpenAIEmbeddings)
    assert embeddings.chunk_size == fake_chunk_size
