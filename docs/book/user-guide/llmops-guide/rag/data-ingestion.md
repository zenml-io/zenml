---
description: Understand how to ingest and preprocess data for RAG pipelines with ZenML.
---

# Data Ingestion and Preprocessing

The first step in setting up a RAG pipeline is to ingest the data that will be
used to train and evaluate the retriever and generator models. This data can
include a large corpus of documents, as well as any relevant metadata or
annotations that can be used to train the retriever and generator.

In the interests of keeping things simple, we'll implement the bulk of what we
need ourselves. However, it's worth noting that there are a number of tools and
frameworks that can help you manage the data ingestion process, including
downloading, preprocessing, and indexing large corpora of documents. ZenML
integrates with a number of these tools and frameworks, making it easy to set up
and manage RAG pipelines.

{% hint style="info" %} You can view all the code referenced in this guide in
the associated project repository. Please [visit the `llm-complete-guide`
project](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide) inside
the ZenML projects repository if you want to dive deeper. {% endhint %}

You can add a ZenML step that scrapes a series of URLs and outputs the URLs quite
easily. Here we assemble a step that scrapes URLs related to ZenML from its documentation.
We leverage some simple helper utilities that we have created for this purpose:

```python
from typing import List
from typing_extensions import Annotated
from zenml import log_artifact_metadata, step
from steps.url_scraping_utils import get_all_pages

@step
def url_scraper(
    docs_url: str = "https://docs.zenml.io",
    repo_url: str = "https://github.com/zenml-io/zenml",
    website_url: str = "https://zenml.io",
) -> Annotated[List[str], "urls"]:
    """Generates a list of relevant URLs to scrape."""
    docs_urls = get_all_pages(docs_url)
    log_artifact_metadata(
        metadata={
            "count": len(docs_urls),
        },
    )
    return docs_urls
```

The `get_all_pages` function simply crawls our documentation website and
retrieves a unique set of URLs. We've limited it to only scrape the
documentation relating to the most recent releases so that we're not mixing old
syntax and information with the new. This is a simple way to ensure that we're
only ingesting the most relevant and up-to-date information into our pipeline.

We also log the count of those URLs as metadata for the step output. This will
be visible in the dashboard for extra visibility around the data that's being
ingested. Of course, you can also add more complex logic to this step, such as
filtering out certain URLs or adding more metadata.

![Partial screenshot from the dashboard showing the metadata from the step](../.gitbook/assets/llm-data-ingestion-metadata.png)

Once we have our list of URLs, we use [the `unstructured`
library](https://github.com/Unstructured-IO/unstructured) to load and parse the
pages. This will allow us to use the text without having to worry about the
details of the HTML structure and/or markup. This specifically helps us keep the
text
content as small as possible since we are operating in a constrained environment
with LLMs.

```python
from typing import List
from unstructured.partition.html import partition_html
from zenml import step

@step
def web_url_loader(urls: List[str]) -> List[str]:
    """Loads documents from a list of URLs."""
    document_texts = []
    for url in urls:
        elements = partition_html(url=url)
        text = "\n\n".join([str(el) for el in elements])
        document_texts.append(text)
    return document_texts
```

The previously-mentioned frameworks offer many more options when it comes to
data ingestion, including the ability to load documents from a variety of
sources, preprocess the text, and extract relevant features. For our purposes,
though, we don't need anything too fancy. 

There are fancier ways to load documents with LangChain, including built-in
scrapers that recursively follow links and load documents. However, for the
purposes of this guide, we'll keep it simple and just load the documents from
the URLs we've scraped. It's also worth noting that the simple
`UnstructuredURLLoader` method is quite powerful and gives you a bit more
control and oversight over the process since recursive scrapers can be prone to
various unexpected failures.

# Preprocessing the data

Once we have loaded the documents, we can preprocess them and update the index
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
