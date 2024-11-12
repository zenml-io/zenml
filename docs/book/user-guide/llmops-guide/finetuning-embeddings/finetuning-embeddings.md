---
description: Finetune embeddings on custom synthetic data to improve retrieval performance.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


We previously learned [how to use RAG with ZenML](../rag-with-zenml/README.md) to
build a production-ready RAG pipeline. In this section, we will explore how to
optimize and maintain your embedding models through synthetic data generation and
human feedback. So far, we've been using off-the-shelf embeddings, which provide
a good baseline and decent performance on standard tasks. However, you can often
significantly improve performance by finetuning embeddings on your own domain-specific data.

Our RAG pipeline uses a retrieval-based approach, where it first retrieves the
most relevant documents from our vector database, and then uses a language model
to generate a response based on those documents. By finetuning our embeddings on
a dataset of technical documentation similar to our target domain, we can improve
the retrieval step and overall performance of the RAG pipeline.

The work of finetuning embeddings based on synthetic data and human feedback is
a multi-step process. We'll go through the following steps:

- [generating synthetic data with `distilabel`](synthetic-data-generation.md)
- [finetuning embeddings with Sentence Transformers](finetuning-embeddings-with-sentence-transformers.md)
- [evaluating finetuned embeddings and using ZenML's model control plane to get a systematic overview](evaluating-finetuned-embeddings.md)

Besides ZenML, we will do this by using two open source libraries:
[`argilla`](https://github.com/argilla-io/argilla/) and
[`distilabel`](https://github.com/argilla-io/distilabel). Both of these
libraries focus optimizing model outputs through improving data quality,
however, each one of them takes a different approach to tackle the same problem.
`distilabel` provides a scalable and reliable approach to distilling knowledge
from LLMs by generating synthetic data or providing AI feedback with LLMs as
judges. `argilla` enables AI engineers and domain experts to collaborate on data
projects by allowing them to organize and explore data through within an
interactive and engaging UI. Both libraries can be used individually but they
work better together. We'll showcase their use via ZenML pipelines.

To follow along with the example explained in this guide, please follow the
instructions in [the `llm-complete-guide` repository](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide) where the full code is also
available. This specific section on embeddings finetuning can be run locally or
using cloud compute as you prefer.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
