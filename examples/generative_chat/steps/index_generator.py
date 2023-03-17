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

from typing import List

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.vectorstores import FAISS, VectorStore

from zenml.steps import step


@step(enable_cache=True)
def index_generator(
    documents: List[Document], slack_documents: List[Document]
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
        chunk_size=1000, chunk_overlap=0
    )
    split_documents = docs_text_splitter.split_documents(documents)

    # chunk the slack documents into smaller chunks
    slack_text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    slack_texts = slack_text_splitter.split_documents(slack_documents)

    split_documents.extend(slack_texts)  # merges the two document lists
    return FAISS.from_documents(documents, embeddings)
