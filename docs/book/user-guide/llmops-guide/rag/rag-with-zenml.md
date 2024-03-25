---
description: RAG is a sensible way to get started with LLMs.
---

# RAG Pipelines with ZenML

Retrieval-Augmented Generation (RAG) is a powerful technique that combines the
strengths of retrieval-based and generation-based models. In this guide, we'll
explore how to set up RAG pipelines with ZenML, including data ingestion, index
store management, and tracking RAG-associated artifacts.

LLMs are a powerful tool, as they can generate human-like responses to a wide
variety of prompts. However, they can also be prone to generating incorrect or
inappropriate responses, especially when the input prompt is ambiguous or
misleading. They are also (currently) limited in the amount of text they can
understand and/or generate. While there are some LLMs [like Google's Gemini 1.5
Pro](https://developers.googleblog.com/2024/02/gemini-15-available-for-private-preview-in-google-ai-studio.html)
that can consistently handle 1 million token, the vast majority (particularly
the open-source ones currently available) handle far less.

{% hint style="info" %} A token is a single unit of text, such as a word or a
punctuation mark. LLMs process text by breaking it down into tokens and then
processing each token sequentially. The number of tokens in a piece of text is a
rough measure of its length and complexity. {% endhint %}

## Understanding Retrieval-Augmented Generation (RAG)

RAG helps us address these problems. We can use this technique to leverage the
strengths of both retrieval-based and generation-based models. It uses a
retriever to find relevant documents from a large corpus and then uses a
generator to produce a response based on the retrieved documents. This approach
is particularly useful for tasks that require contextual understanding and
long-form generation, such as question answering, summarization, and dialogue
generation.

RAG helps with the context limitations mentioned above by providing a way to
retrieve relevant documents that can be used to generate a response. This
retrieval step can help ensure that the generated response is grounded in
relevant information, reducing the likelihood of generating incorrect or
inappropriate responses. It also helps with the token limitations by allowing
the generator to focus on a smaller set of relevant documents, rather than
having to process an entire large corpus.

Given the costs associated with running LLMs, RAG can also be more
cost-effective than using a pure generation-based approach, as it allows you to
focus the generator's resources on a smaller set of relevant documents. This can
be particularly important when working with large corpora or when deploying
models to resource-constrained environments.

## Data Ingestion

The first step in setting up a RAG pipeline is to ingest the data that will be
used to train and evaluate the retriever and generator models. This data can
include a large corpus of documents, as well as any relevant metadata or
annotations that can be used to train the retriever and generator.

[LangChain](https://github.com/langchain-ai/langchain) and
[LlamaIndex](https://github.com/run-llama/llama_index) are two popular
frameworks that offer a variety of tools and functionality for ingesting and
managing large corpora of documents. These frameworks can help you manage the
data ingestion process, including downloading, preprocessing, and indexing large
corpora of documents. ZenML integrates with both LangChain and LlamaIndex as
part of its support for RAG pipelines.

{% hint style="info" %} You can view all the code referenced in this guide in
the associated project repository. Please [visit the `llm-agents`
project](https://github.com/zenml-io/zenml-projects/tree/main/llm-agents) inside
the ZenML projects repository if you want to dive deeper. {% endhint %}

You can add a ZenML step that scraps a series of URLs and outputs the URLs quite
easily. Here we assemble a step that scrapes URLs related to the ZenML project.
We leverage some simple helper utilities that we have created for this purpose:

```python
from typing import List
from typing_extensions import Annotated
from steps.url_scraping_utils import get_all_pages, get_nested_readme_urls
from zenml import step, log_artifact_metadata


@step
def url_scraper(
    docs_url: str = "https://docs.zenml.io",
    repo_url: str = "https://github.com/zenml-io/zenml",
    website_url: str = "https://zenml.io",
) -> Annotated[List[str], "urls"]:
    """Generates a list of relevant URLs to scrape."""


    examples_readme_urls = get_nested_readme_urls(repo_url)
    docs_urls = get_all_pages(docs_url)
    website_urls = get_all_pages(website_url)
    all_urls = docs_urls + website_urls + examples_readme_urls
    log_artifact_metadata(
        metadata={
            "count": len(all_urls),
        },
    )
    return all_urls
```

We also log the count of those URLs as metadata for the step output. This will
be visible in the dashboard for extra visibility around the data that's being
ingested. Of course, you can also add more complex logic to this step, such as
filtering out certain URLs or adding more metadata.

Once we have our list of URLs, we can use some `langchain` utilities to load the
documents into memory:

```python
from typing import List

from langchain.docstore.document import Document
from langchain.document_loaders import UnstructuredURLLoader
from zenml import step


@step
def web_url_loader(urls: List[str]) -> List[Document]:
    """Loads documents from a list of URLs."""
    loader = UnstructuredURLLoader(
        urls=urls,
    )
    return loader.load()
```

There are fancier ways to load documents with LangChain, including built-in
scrapers that recursively follow links and load documents. However, for the
purposes of this guide, we'll keep it simple and just load the documents from
the URLs we've scraped. It's also worth noting that the simple
`UnstructuredURLLoader` method is quite powerful and gives you a bit more
control and oversight over the process since recursive scrapers can be prone to
various unexpected failures.

## Preprocessing and Updating an Index Store

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

## Using our Index Store for a Chatbot

Now that we have our index store, we can use it to create a chatbot that can
answer questions based on the documents in the index store. We can use the
`langchain` library to create a chatbot that uses the index store to retrieve
relevant documents and then generate a response based on those documents.

Here's an example of how you might do this using the `ConversationalChatAgent`.
The advantage of using a framework to handle this part is that it abstracts away
the complexity of managing the retriever and generator models, allowing you to
focus on building the chatbot and integrating it into your application.

```python
from typing import Dict
from typing_extensions import Annotated

from agent.agent_executor_materializer import AgentExecutorMaterializer
from agent.prompt import PREFIX, SUFFIX
from langchain.agents import ConversationalChatAgent
from langchain.chat_models import ChatOpenAI
from langchain.schema.vectorstore import VectorStore
from langchain.tools.vectorstore.tool import VectorStoreQATool
from langchain.agents import AgentExecutor
from pydantic import BaseModel
from zenml import step, ArtifactConfig, log_artifact_metadata


PIPELINE_NAME = "zenml_agent_creation_pipeline"
# Choose what character to use for your agent's answers
CHARACTER = "technical assistant"


class AgentParameters(BaseModel):
    """Parameters for the agent."""

    llm: Dict = {
        "temperature": 0,
        "max_tokens": 1000,
        "model_name": "gpt-3.5-turbo",
    }

    # allow extra fields
    class Config:
        extra = "ignore"


@step(output_materializers=AgentExecutorMaterializer)
def agent_creator(
    vector_store: VectorStore, config: AgentParameters = AgentParameters()
) -> Annotated[
    AgentExecutor, ArtifactConfig(name="agent", is_model_artifact=True)
]:
    """Create an agent from a vector store.

    Args:
        vector_store: Vector store to create agent from.

    Returns:
        An AgentExecutor.
    """
    tools = [
        VectorStoreQATool(
            name=f"zenml-qa-tool",
            vectorstore=vector_store,
            description="Use this tool to answer questions about ZenML. "
            "How to debug errors in ZenML, how to answer conceptual "
            "questions about ZenML like available features, existing abstractions, "
            "and other parts from the documentation.",
            llm=ChatOpenAI(**config.llm),
        ),
    ]

    system_prompt = PREFIX.format(character=CHARACTER)

    my_agent = ConversationalChatAgent.from_llm_and_tools(
        llm=ChatOpenAI(**config.llm),
        tools=tools,
        system_message=system_prompt,
        human_message=SUFFIX,
    )

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=my_agent,
        tools=tools,
        verbose=True,
    )

    log_artifact_metadata(
        artifact_name="agent",
        metadata={
            "Tools and their descriptions": {
                tool.name: tool.description for tool in tools
            },
            "Personality": {
                "character": CHARACTER,
                "temperature": config.llm["temperature"],
                "model_name": config.llm["model_name"],
            },
        },
    )

    return agent_executor
```

The other benefit of the step returning an agent is that you might choose to
enhance that agent with more tools or extra capabilities. For example, you could
add a search tool that allows the agent to search online for answers alongside
the documents we have in the index store, and you can tweak the personality
using parameters such as the temperature, model name, and character.

## Tracking RAG-Associated Artifacts with ZenML

You can see in the code above how we've manually logged the metadata for the
artifacts that are generated by the pipeline. This is a good practice to follow
because it allows you to track the evolution of the pipeline over time and
understand how changes to the pipeline affect the performance of the RAG models.

ZenML allows you to track all the artifacts associated with your RAG pipeline,
from hyperparameters and model weights to metadata and performance metrics, as
well as all the RAG or LLM-specific artifacts like chains, agents, tokenizers
and vector stores. These can all be tracked in the [Model Control
Plane](../advanced-guide/data-management/model-management.md) and thus
visualized in the [ZenML Cloud](https://zenml.io/cloud).

By bringing all of the above into [a simple ZenML
pipeline](https://github.com/zenml-io/zenml-projects/blob/main/llm-agents/pipelines/agent_creator.py)
we achieve a clearly delineated set of steps that can be run and rerun to set up
our basic RAG pipeline. This is a great starting point for building out more
complex RAG pipelines, and it's a great way to get started with LLMs in a
sensible way.

Some of the advantages that ZenML brings to the table here include:

- **Reproducibility**: You can rerun the pipeline to update the index store with
  new documents or to change the parameters of the agent. Previous versions of
  the artifacts will be preserved, and you can compare the performance of
    different versions of the pipeline.
- **Scalability**: You can easily scale the pipeline to handle larger corpora of
    documents by deploying it on a cloud provider and using a more scalable
    vector store.
- **Tracking artifacts and associating them with metadata**: You can track the
    artifacts generated by the pipeline and associate them with metadata that
    provides additional context and insights into the pipeline. This metadata
    and these artifacts are then visible in the ZenML dashboard, allowing you to
    monitor the performance of the pipeline and debug any issues that arise.
- **Maintainability** - Having your pipeline in a clear, modular format makes it
    easier to maintain and update. You can easily add new steps, change the
    parameters of existing steps, and experiment with different configurations
    to see how they affect the performance of the pipeline.
- **Collaboration** - You can share the pipeline with your team and collaborate
    on it together. You can also use the ZenML dashboard to share insights and
    findings with your team, making it easier to work together on the pipeline.

In the next section, we'll explore how to set up finetuning scenarios with ZenML
to further enhance the performance of our RAG pipeline. RAG gets us a long way
towards building a powerful chatbot, but finetuning the models can help us
further improve the quality of the responses and make the chatbot more
responsive to the specific needs of our users. We'll also explore how to
integrate finetuning into ZenML pipelines and discuss best practices for data
preparation, hyperparameter tuning, and monitoring.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
