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
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain.docstore.document import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.indices.vector_store.vector_indices import (
    GPTFaissIndex,
)
from llama_index.readers.schema.base import Document

from tests.mock_utils.mock_decorator import patch_common
from tests.mock_utils.mock_prompts import (
    MOCK_REFINE_PROMPT,
    MOCK_TEXT_QA_PROMPT,
)
from tests.unit.test_general import _test_materializer
from zenml.integrations.llama_index.materializers.gpt_index_materializer import (
    LlamaIndexGPTIndexMaterializer,
)


@pytest.fixture
def struct_kwargs() -> Tuple[Dict, Dict]:
    """Index kwargs."""
    index_kwargs = {
        "text_qa_template": MOCK_TEXT_QA_PROMPT,
    }
    query_kwargs = {
        "text_qa_template": MOCK_TEXT_QA_PROMPT,
        "refine_template": MOCK_REFINE_PROMPT,
        "similarity_top_k": 1,
    }
    return index_kwargs, query_kwargs


@pytest.fixture
def documents() -> List[Document]:
    """Get documents."""
    # NOTE: one document for now
    doc_text = (
        "Hello world.\n"
        "This is a test.\n"
        "This is another test.\n"
        "This is a test v2."
    )
    return [Document(doc_text)]


class MockFaissIndex:
    """Mock Faiss index."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize params."""
        self._index: Dict[int, np.ndarray] = {}

    @property
    def ntotal(self) -> int:
        """Get ntotal."""
        return len(self._index)

    def add(self, vecs: np.ndarray) -> None:
        """Add vectors to index."""
        for vec in vecs:
            new_id = len(self._index)
            self._index[new_id] = vec

    def reset(self) -> None:
        """Reset index."""
        self._index = {}

    def search(self, vec: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search index."""
        # assume query vec is of the form 1 x k
        # index_mat is n x k
        index_mat = np.array(list(self._index.values()))
        # compute distances
        distances = np.linalg.norm(index_mat - vec, axis=1)

        indices = np.argsort(distances)[:k]
        sorted_distances = distances[indices][:k]

        # return distances and indices
        return sorted_distances[np.newaxis, :], indices[np.newaxis, :]


def mock_get_text_embedding(text: str) -> List[float]:
    """Mock get text embedding."""
    # assume dimensions are 5
    if text == "Hello world.":
        return [1, 0, 0, 0, 0]
    elif text == "This is a test.":
        return [0, 1, 0, 0, 0]
    elif text == "This is another test.":
        return [0, 0, 1, 0, 0]
    elif text == "This is a test v2.":
        return [0, 0, 0, 1, 0]
    elif text == "This is a test v3.":
        return [0, 0, 0, 0, 1]
    elif text == "This is bar test.":
        return [0, 0, 1, 0, 0]
    elif text == "Hello world backup.":
        # this is used when "Hello world." is deleted.
        return [1, 0, 0, 0, 0]
    else:
        raise ValueError("Invalid text for `mock_get_text_embedding`.")


def mock_get_text_embeddings(texts: List[str]) -> List[List[float]]:
    """Mock get text embeddings."""
    return [mock_get_text_embedding(text) for text in texts]


@patch_common
@patch.object(
    OpenAIEmbedding, "_get_text_embedding", side_effect=mock_get_text_embedding
)
@patch.object(
    OpenAIEmbedding,
    "_get_text_embeddings",
    side_effect=mock_get_text_embeddings,
)
def test_llama_index_gpt_index_materializer(
    clean_client,
    documents: List[Document],
    struct_kwargs: Dict,
):
    """Test the Llama Index GPT Index materializer."""
    # NOTE: mock faiss import
    sys.modules["faiss"] = MagicMock()
    # NOTE: mock faiss index
    faiss_index = MockFaissIndex()

    index_kwargs, _ = struct_kwargs

    faiss = GPTFaissIndex(
        documents=documents, faiss_index=faiss_index, **index_kwargs
    )
    assert len(faiss.index_struct.nodes_dict) == 4
    # check contents of nodes
    assert faiss.index_struct.get_node("0").text == "Hello world."
    assert faiss.index_struct.get_node("1").text == "This is a test."
    assert faiss.index_struct.get_node("2").text == "This is another test."
    assert faiss.index_struct.get_node("3").text == "This is a test v2."

    with does_not_raise():
        index = _test_materializer(
            step_output=faiss,
            materializer_class=LlamaIndexGPTIndexMaterializer,
        )

        assert len(index.index_struct.nodes_dict) == 4

        assert index.index_struct.get_node("0").text == "Hello world."
        assert index.index_struct.get_node("1").text == "This is a test."
        assert index.index_struct.get_node("2").text == "This is another test."
        assert index.index_struct.get_node("3").text == "This is a test v2."
