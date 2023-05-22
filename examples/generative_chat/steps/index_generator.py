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

import random
from typing import List

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.vectorstores import FAISS, VectorStore
from openai.error import InvalidRequestError

from zenml import step
from zenml.logger import get_logger
from zenml.steps.base_parameters import BaseParameters

logger = get_logger(__name__)


class IndexGeneratorParameters(BaseParameters):
    """Params for index generator.

    Attributes:
        document_chunk_size: Size of the document chunks.
        document_chunk_overlap: Overlap of the document chunks.
        slack_chunk_size: Size of the slack chunks.
        slack_chunk_overlap: Overlap of the slack chunks.
    """

    document_chunk_size: int = 1000
    document_chunk_overlap: int = 0
    slack_chunk_size: int = 1000
    slack_chunk_overlap: int = 200


@step(enable_cache=True)
def index_generator(
    documents: List[Document],
    slack_documents: List[Document],
    params: IndexGeneratorParameters,
) -> VectorStore:
    """Generates a FAISS index from a list of documents.

    Args:
        documents: List of langchain documents.
        slack_documents: List of langchain documents.

    Returns:
        FAISS index.
    """
    embeddings = OpenAIEmbeddings()

    # chunk the documents into smaller chunks
    docs_text_splitter = CharacterTextSplitter(
        chunk_size=params.document_chunk_size,
        chunk_overlap=params.document_chunk_overlap,
    )
    split_documents = docs_text_splitter.split_documents(documents)

    # chunk the slack documents into smaller chunks
    slack_text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=params.slack_chunk_size,
        chunk_overlap=params.slack_chunk_overlap,
    )
    slack_texts = slack_text_splitter.split_documents(slack_documents)

    split_documents.extend(slack_texts)  # merges the two document lists

    try:
        return FAISS.from_documents(documents, embeddings)
    except InvalidRequestError:
        random.shuffle(documents)
        shorter_documents = documents[: len(documents) // 2]
        logger.warning(
            "Too many tokens passed to OpenAI. Trying with smaller set of documents"
        )
        return FAISS.from_documents(shorter_documents, embeddings)
