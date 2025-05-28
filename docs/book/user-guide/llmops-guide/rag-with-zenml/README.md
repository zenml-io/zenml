---
description: RAG is a sensible way to get started with LLMs.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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
that can consistently handle 1 million tokens (small units of text), the vast majority (particularly
the open-source ones currently available) handle far less.

The first part of this guide to RAG pipelines with ZenML is about understanding
the basic components and how they work together. We'll cover the following
topics:

- why RAG exists and what problem it solves
- how to ingest and preprocess data that we'll use in our RAG pipeline
- how to leverage embeddings to represent our data; this will be the basis for
  our retrieval mechanism
- how to store these embeddings in a vector database
- how to track RAG-associated artifacts with ZenML

At the end, we'll bring it all together and show all the components working
together to perform basic RAG inference.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
