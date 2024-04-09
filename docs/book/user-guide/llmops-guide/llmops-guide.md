---
description: Leverage the power of LLMs in your MLOps workflows with ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Welcome to the ZenML LLMOps Guide, where we dive into the exciting world of Large Language Models (LLMs) and how to integrate them seamlessly into your MLOps pipelines using ZenML. This guide is designed for ML practitioners and MLOps engineers looking to harness the potential of LLMs while maintaining the robustness and scalability of their workflows.

<figure><img src="/docs/book/.gitbook/assets/rag-overview.png" alt=""><figcaption><p>ZenML simplifies the development and deployment of LLM-powered MLOps pipelines.</p></figcaption></figure>

In this guide, we'll explore various aspects of working with LLMs in ZenML, including:

* [RAG with ZenML](rag/rag-with-zenml.md)
  * [Understanding Retrieval-Augmented Generation (RAG)](rag/understanding-rag.md)
  * [Data ingestion and preprocessing](rag/data-ingestion.md)
  * [Embeddings generation](rag/embeddings-generation.md)
  * [Storing embeddings in a vector database](rag/storing-embeddings-in-a-vector-database.md)
  * [Basic RAG inference pipeline](rag/basic-rag-inference-pipeline.md)
* [Improve retrieval by finetuning embeddings](finetuning-embeddings/finetuning-embeddings.md)
* [Reranking for better retrieval](reranking/reranking.md)
* [Finetuning LLMs with ZenML](finetuning-llms/finetuning-llms.md)

To follow along with the examples and tutorials in this guide, ensure you have a
Python environment set up with ZenML installed. Familiarity with the concepts
covered in the [Starter Guide](../starter-guide/) and [Production
Guide](../production-guide/) is recommended.

We'll showcase a specific application over the course of this LLM guide, showing
how you can work from a simple RAG pipeline to a more complex setup that
involves
finetuning embeddings, reranking retrieved documents, and even finetuning the
LLM itself. We'll do this all for a use case relevant to ZenML: a question
answering system that can provide answers to common questions about ZenML. This
will help you understand how to apply the concepts covered in this guide to your
own projects.

By the end of this guide, you'll have a solid understanding of how to leverage
LLMs in your MLOps workflows using ZenML, enabling you to build powerful,
scalable, and maintainable LLM-powered applications. Let's get started!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
