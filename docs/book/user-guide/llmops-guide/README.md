---
icon: robot
description: Leverage the power of LLMs in your MLOps workflows with ZenML.
---

# LLMOps guide

Welcome to the ZenML LLMOps Guide, where we dive into the exciting world of Large Language Models (LLMs) and how to integrate them seamlessly into your MLOps pipelines using ZenML. This guide is designed for ML practitioners and MLOps engineers looking to harness the potential of LLMs while maintaining the robustness and scalability of their workflows.

<figure><img src="../../.gitbook/assets/rag-overview.png" alt=""><figcaption><p>ZenML simplifies the development and deployment of LLM-powered MLOps pipelines.</p></figcaption></figure>

In this guide, we'll explore various aspects of working with LLMs in ZenML, including:

* [RAG with ZenML](rag-with-zenml/README.md)
  * [RAG in 85 lines of code](rag-with-zenml/rag-85-loc.md)
  * [Understanding Retrieval-Augmented Generation (RAG)](rag-with-zenml/understanding-rag.md)
  * [Data ingestion and preprocessing](rag-with-zenml/data-ingestion.md)
  * [Embeddings generation](rag-with-zenml/embeddings-generation.md)
  * [Storing embeddings in a vector database](rag-with-zenml/storing-embeddings-in-a-vector-database.md)
  * [Basic RAG inference pipeline](rag-with-zenml/basic-rag-inference-pipeline.md)
* [Evaluation and metrics](evaluation/README.md)
  * [Evaluation in 65 lines of code](evaluation/evaluation-in-65-loc.md)
  * [Retrieval evaluation](evaluation/retrieval.md)
  * [Generation evaluation](evaluation/generation.md)
  * [Evaluation in practice](evaluation/evaluation-in-practice.md)
* [Reranking for better retrieval](reranking/README.md)
  * [Understanding reranking](reranking/understanding-reranking.md)
  * [Implementing reranking in ZenML](reranking/implementing-reranking.md)
  * [Evaluating reranking performance](reranking/evaluating-reranking-performance.md)
* [Improve retrieval by finetuning embeddings](finetuning-embeddings/finetuning-embeddings.md)
  * [Synthetic data generation](finetuning-embeddings/synthetic-data-generation.md)
  * [Finetuning embeddings with Sentence Transformers](finetuning-embeddings/finetuning-embeddings-with-sentence-transformers.md)
  * [Evaluating finetuned embeddings](finetuning-embeddings/evaluating-finetuned-embeddings.md)
* [Finetuning LLMs with ZenML](finetuning-llms/finetuning-llms.md)
  * [Finetuning in 100 lines of code](finetuning-llms/finetuning-100-loc.md)
  * [Why and when to finetune LLMs](finetuning-llms/why-and-when-to-finetune-llms.md)
  * [Starter choices with finetuning](finetuning-llms/starter-choices-for-finetuning-llms.md)
  * [Finetuning with 🤗 Accelerate](finetuning-llms/finetuning-with-accelerate.md)
  * [Evaluation for finetuning](finetuning-llms/evaluation-for-finetuning.md)
  * [Deploying finetuned models](finetuning-llms/deploying-finetuned-models.md)
  * [Next steps](finetuning-llms/next-steps.md)

To follow along with the examples and tutorials in this guide, ensure you have a Python environment set up with ZenML installed. Familiarity with the concepts covered in the [Starter Guide](../starter-guide/README.md) and [Production Guide](../production-guide/README.md) is recommended.

We'll showcase a specific application over the course of this LLM guide, showing how you can work from a simple RAG pipeline to a more complex setup that involves finetuning embeddings, reranking retrieved documents, and even finetuning the LLM itself. We'll do this all for a use case relevant to ZenML: a question answering system that can provide answers to common questions about ZenML. This will help you understand how to apply the concepts covered in this guide to your own projects.

By the end of this guide, you'll have a solid understanding of how to leverage LLMs in your MLOps workflows using ZenML, enabling you to build powerful, scalable, and maintainable LLM-powered applications. First up, let's take a look at a super simple implementation of the RAG paradigm to get started.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
