---
description: Finetune embeddings with Sentence Transformers.
---

We now have a dataset that we can use to finetune our embeddings. You can
[inspect the positive and negative examples](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions_0_60_0_distilabel) on the Hugging Face [datasets page](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions_0_60_0_distilabel) since
our previous pipeline pushed the data there.

![Synthetic data generated with distilabel for embeddings finetuning](../../../.gitbook/assets/distilabel-synthetic-dataset-hf.png)

Our pipeline for finetuning the embeddings is relatively simple. We'll do the
following:

- load our data either from Hugging Face or [from Argilla via the ZenML
  annotation integration](../../../component-guide/annotators/argilla.md)
- finetune our model using the [Sentence
  Transformers](https://www.sbert.net/) library
- evaluate the base and finetuned embeddings
- visualise the results of the evaluation

![Embeddings finetuning pipeline with Sentence Transformers and ZenML](../../../.gitbook/assets/rag-finetuning-embeddings-pipeline.png)

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


