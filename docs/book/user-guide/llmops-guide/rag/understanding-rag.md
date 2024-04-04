---
description: Understand the Retrieval-Augmented Generation (RAG) technique and its benefits.
---

# Understanding Retrieval-Augmented Generation (RAG)

LLMs are powerful but not without their limitations. They are prone to
generating incorrect responses, especially when it's unclear what the input
prompt is asking for. They are also limited in the amount of text they can
understand and generate. While some LLMs can handle more than 1 million tokens
of input, most open-source models can handle far less.

RAG, [originally proposed in 2020](https://arxiv.org/abs/2005.11401v4) by researchers at Facebook, is a technique that
supplements the inbuilt abilities of foundation models like LLMs with a
retrieval mechanism. This mechanism retrieves relevant documents from a large
corpus and uses them to generate a response. This approach combines the
strengths of retrieval-based and generation-based models, allowing you to
leverage the power of LLMs while addressing their limitations.

# What exactly happens in a RAG pipeline?

![](/docs/book/.gitbook/assets/rag-process-whole.png)

In a RAG pipeline, we use a retriever to find relevant documents from a large corpus and then uses a
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

# When is RAG a good choice?

![](/docs/book/.gitbook/assets/rag-when.png)

RAG is a good choice when you need to generate long-form responses that require
contextual understanding and when you have access to a large corpus of relevant
documents. It can be particularly useful for tasks like question answering,
summarization, and dialogue generation, where the generated response needs to
be grounded in relevant information.

It's often the first thing that you'll want to try when dipping your toes into
the world of LLMs. This is because it provides a sensible way to get a feel for
how the process works, and it doesn't require as much data or computational
resources as other approaches. It's also a good choice when you need to balance
the benefits of LLMs with the limitations of the current generation of models.

# How does RAG fit into the ZenML ecosystem?

![](/docs/book/.gitbook/assets/rag-and-zenml.png)

In ZenML, you can set up RAG pipelines that combine the strengths of
retrieval-based and generation-based models. This allows you to leverage the
power of LLMs while addressing their limitations. ZenML provides tools for data
ingestion, index store management, and tracking RAG-associated artifacts, making
it easy to set up and manage RAG pipelines.

ZenML also provides a way to scale beyond the limitations of simple RAG
pipelines, as we shall see in later sections of this guide. While you might
start off with something simple, at a later point you might want to transition
to a more complex setup that involves finetuning embeddings, reranking
retrieved documents, or even finetuning the LLM itself. ZenML provides tools for
all of these scenarios, making it easy to scale your RAG pipelines as needed.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
