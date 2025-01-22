---
description: Add reranking to your RAG inference for better retrieval performance.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Rerankers are a crucial component of retrieval systems that use LLMs. They help
improve the quality of the retrieved documents by reordering them based on
additional features or scores. In this section, we'll explore how to add a
reranker to your RAG inference pipeline in ZenML.

In previous sections, we set up the overall workflow, from data ingestion and
preprocessing to embeddings generation and retrieval. We then set up some basic
evaluation metrics to assess the performance of our retrieval system. A reranker
is a way to squeeze a bit of extra performance out of the system by reordering
the retrieved documents based on additional features or scores.

![](/docs/book/.gitbook/assets/reranking-workflow.png)

As you can see, reranking is an optional addition we make to what we've already
set up. It's not strictly necessary, but it can help improve the relevance and
quality of the retrieved documents, which in turn can lead to better responses
from the LLM. Let's dive in!


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
