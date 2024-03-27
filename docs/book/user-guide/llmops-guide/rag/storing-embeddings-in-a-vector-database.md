---
description: Store embeddings in a vector database for efficient retrieval.
---

# Storing Embeddings in a Vector Database



 and update the index
store. This is a crucial step in the RAG pipeline, as it ensures that the
retriever has access to the most up-to-date and relevant documents. The
preprocessing step can include a variety of tasks, such as cleaning and
normalizing the text, extracting relevant features, and updating the index store
with the new documents.

For the purposes of simplicity we show this using an in-memory vector database
(the FAISS vector database). This is a simple way to index documents and is
suitable for small to medium-sized corpora. For larger corpora, you would want
to use a more scalable solution, most likely deployed on a cloud provider.

```python
from typing_extensions import Annotated
from typing import List

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
)
from langchain.schema.vectorstore import VectorStore
from langchain.vectorstores.faiss import FAISS
from zenml import step, log_artifact_metadata


@step
def index_generator(
    documents: List[Document],
) -> Annotated[VectorStore, "vector_store"]:
    """Generates a vector store from a list of documents."""
    embeddings = OpenAIEmbeddings()

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    compiled_texts = text_splitter.split_documents(documents)

    log_artifact_metadata(
        artifact_name="vector_store",
        metadata={
            "embedding_type": "OpenAIEmbeddings",
            "vector_store_type": "FAISS",
        },
    )

    return FAISS.from_documents(compiled_texts, embeddings)
```

Before data is ingested into the vector store, it is split into chunks of 1000
characters with a 0 character overlap. This is a simple way to ensure that the
documents are split into manageable chunks that can be processed by the
retriever and generator models. The vector store is then generated from the
compiled texts using the OpenAIEmbeddings and FAISS vector store types.
Adjusting the chunk size and chunk overlap are both parameters that you might
want to experiment with to see how they affect the performance of your RAG
pipeline.

We make sure to log the metadata for the artifact, including the embedding type
and the vector store type. This will be visible in the dashboard and can be
useful for debugging and understanding the pipeline. It also allows you to track
the evolution of the pipeline over time.

So now we have a vector store that we can use to retrieve documents. We
populated the index store with documents that are meaningful to our use case so
that we can retrieve chunks that are relevant to questions passed into our RAG
pipeline.







<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
