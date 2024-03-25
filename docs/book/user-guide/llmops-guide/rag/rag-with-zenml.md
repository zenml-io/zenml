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

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
