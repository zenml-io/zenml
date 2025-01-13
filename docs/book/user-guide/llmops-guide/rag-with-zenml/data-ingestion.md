---
description: Understand how to ingest and preprocess data for RAG pipelines with ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The first step in setting up a RAG pipeline is to ingest the data that will be
used to train and evaluate the retriever and generator models. This data can
include a large corpus of documents, as well as any relevant metadata or
annotations that can be used to train the retriever and generator.

![](/docs/book/.gitbook/assets/rag-stage-1.png)

In the interests of keeping things simple, we'll implement the bulk of what we
need ourselves. However, it's worth noting that there are a number of tools and
frameworks that can help you manage the data ingestion process, including
downloading, preprocessing, and indexing large corpora of documents. ZenML
integrates with a number of these tools and frameworks, making it easy to set up
and manage RAG pipelines.

{% hint style="info" %}
You can view all the code referenced in this guide in the associated project
repository. Please visit <a
href="https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide">the
`llm-complete-guide` project</a> inside the ZenML projects repository if you
want to dive deeper.
{% endhint %}

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

![Partial screenshot from the dashboard showing the metadata from the step](/docs/book/.gitbook/assets/llm-data-ingestion-metadata.png)

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
though, we don't need anything too fancy. It also makes our pipeline easier to
debug since we can see exactly what's being loaded and how it's being processed.
You don't get that same level of visibility with more complex frameworks.

# Preprocessing the data

Once we have loaded the documents, we can preprocess them into a form that's
useful for a RAG pipeline. There are a lot of options here, depending on how
complex you want to get, but to start with you can think of the 'chunk size' as
one of the key parameters to think about.

Our text is currently in the form of various long strings, with each one
representing a single web page. These are going to be too long to pass into our
LLM, especially if we care about the speed at which we get our answers back. So
the strategy here is to split our text into smaller chunks that can be processed
more efficiently. There's a sweet spot between having tiny chunks, which will
make it harder for our search / retrieval step to find relevant information to
pass into the LLM, and having large chunks, which will make it harder for the
LLM to process the text.

```python
import logging
from typing import Annotated, List
from utils.llm_utils import split_documents
from zenml import ArtifactConfig, log_artifact_metadata, step

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@step(enable_cache=False)
def preprocess_documents(
    documents: List[str],
) -> Annotated[List[str], ArtifactConfig(name="split_chunks")]:
    """Preprocesses a list of documents by splitting them into chunks."""
    try:
        log_artifact_metadata(
            artifact_name="split_chunks",
            metadata={
                "chunk_size": 500,
                "chunk_overlap": 50
            },
        )
        return split_documents(
            documents, chunk_size=500, chunk_overlap=50
        )
    except Exception as e:
        logger.error(f"Error in preprocess_documents: {e}")
        raise
```

It's really important to know your data to have a good intuition about what kind
of chunk size might make sense. If your data is structured in such a way where
you need large paragraphs to capture a particular concept, then you might want a
larger chunk size. If your data is more conversational or question-and-answer
based, then you might want a smaller chunk size.

For our purposes, given that we're working with web pages that are written as
documentation for a software library, we're going to use a chunk size of 500 and
we'll make sure that the chunks overlap by 50 characters. This means that we'll
have a lot of overlap between our chunks, which can be useful for ensuring that
we don't miss any important information when we're splitting up our text.

Again, depending on your data and use case, there is more you might want to do
with your data. You might want to clean the text, remove code snippets or make
sure that code snippets were not split across chunks, or even extract metadata
from the text. This is a good starting point, but you can always add more
complexity as needed.

Next up, generating embeddings so that we can use them to retrieve relevant
documents...

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide)
repository and particularly [the code for the steps](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide/steps/) in this section. Note, too,
that a lot of the logic is encapsulated in utility functions inside [`url_scraping_utils.py`](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide/steps/url_scraping_utils.py).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
