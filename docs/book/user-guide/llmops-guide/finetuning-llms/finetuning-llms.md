---
description: Finetune LLMs for specific tasks or to improve performance and cost.
---

So far in our LLMOps journey we've learned [how to use RAG with
ZenML](../rag-with-zenml/README.md), how to [evaluate our RAG
systems](../evaluation/README.md), how to [use reranking to improve retrieval](../reranking/README.md), and how to
[finetune embeddings](../finetuning-embeddings/finetuning-embeddings.md) to
support and improve our RAG systems. In this section we will explore LLM
finetuning itself. So far we've been using APIs like OpenAI and Anthropic, but
there are some scenarios where it makes sense to finetune an LLM on your own
data. We'll get into those scenarios and how to finetune an LLM in the pages
that follow.

While RAG systems are excellent at retrieving and leveraging external knowledge,
there are scenarios where finetuning an LLM can provide additional benefits even
with a RAG system in place. For example, you might want to finetune an LLM to
improve its ability to generate responses in a specific format, to better
understand domain-specific terminology and concepts that appear in your
retrieved content, or to reduce the length of prompts needed for consistent
outputs. Finetuning can also help when you need the model to follow very
specific patterns or protocols that would be cumbersome to encode in prompts, or
when you want to optimize for latency by reducing the context window needed for
good performance.

We'll go through the following steps in this guide:

- [Finetuning in 100 lines of code](finetuning-100-loc.md)
- [Why and when to finetune LLMs](why-and-when-to-finetune-llms.md)
- [Starter choices with finetuning](getting-started-with-finetuning.md)
- [Finetuning with 🤗 Accelerate](finetuning-with-accelerate.md)
- [Evaluation for finetuning](evaluation-for-finetuning.md)
- [Deploying finetuned models](deploying-finetuned-models.md)
- [Next steps](next-steps.md)

This guide is slightly different from the others in that we don't follow a
specific use case as the model for finetuning LLMs. The actual steps needed to
finetune an LLM are not that complex, but the important part is to understand
when you might need to finetune an LLM, how to evaluate the performance of what
you do as well as decisions around what data to use and so on.

To follow along with the example explained in this guide, please follow the
instructions in [the `llm-lora-finetuning` repository](https://github.com/zenml-io/zenml-projects/tree/main/llm-lora-finetuning) where the full code is also
available. This code can be run locally (if you have a GPU attached to your
machine) or using cloud compute as you prefer.
