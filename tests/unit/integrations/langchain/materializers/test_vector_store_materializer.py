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
import sys
from contextlib import ExitStack as does_not_raise

import pytest

from tests.unit.test_general import _test_materializer
from zenml.integrations.langchain.materializers.vector_store_materializer import (
    LangchainVectorStoreMaterializer,
)


@pytest.mark.skipif(
    sys.version_info.major == 3 and sys.version_info.minor <= 7,
    reason="Langchain is only supported on Python >=3.8",
)
def test_langchain_vector_store_materializer(clean_client):
    """Test the Langchain Vector Store materializer."""
    from langchain.docstore.document import Document
    from langchain.embeddings.fake import FakeEmbeddings
    from langchain.vectorstores.faiss import FAISS

    page_content = "Axl, Aria and Blupus went to the sea for a picnic."
    fake_embeddings = FakeEmbeddings(size=1)
    with does_not_raise():
        vector_store = FAISS.from_documents(
            documents=[Document(page_content=page_content)],
            embedding=fake_embeddings,
        )
        _test_materializer(
            step_output=vector_store,
            materializer_class=LangchainVectorStoreMaterializer,
        )
