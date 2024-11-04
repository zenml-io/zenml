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


def test_langchain_vectorstore_materializer(clean_client):
    """Tests the Langchain Vector Store materializer."""
    from langchain_community.embeddings import FakeEmbeddings
    from langchain_community.vectorstores import SKLearnVectorStore

    from zenml.integrations.langchain.materializers.vector_store_materializer import (
        LangchainVectorStoreMaterializer,
    )

    embeddings = FakeEmbeddings(size=1352)

    langchain_vector_store = _test_materializer(
        step_output=SKLearnVectorStore(embedding=embeddings),
        materializer_class=LangchainVectorStoreMaterializer,
        expected_metadata_size=1,
    )

    assert langchain_vector_store.embeddings
