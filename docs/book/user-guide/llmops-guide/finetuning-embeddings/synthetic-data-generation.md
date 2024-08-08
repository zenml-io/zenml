---
description: Generate synthetic data with distilabel to finetune embeddings.
---

We already have [a dataset of technical documentation](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions_0_60_0) that was generated
previously while we were working on the RAG pipeline. We'll use this dataset
to generate synthetic data with `distilabel`. You can inspect the data directly
[on the Hugging Face dataset page](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions_0_60_0).

![](../../.gitbook/assets/rag-dataset-hf.png)

As you can see, it is made up of some `page_content` (our chunks) as well as the
source URL from where the chunk was taken from. With embeddings, what we're
going to want to do is pair the `page_content` with a question that we want to
answer. In a pre-LLM world we might have actually created a new column and
worked to manually craft questions for each chunk. However, with LLMs, we can
use the `page_content` to generate questions.

Our pipeline to generate synthetic data will look like this:

![](../../.gitbook/assets/rag-synthetic-data-pipeline.png)

We'll load the Hugging Face dataset, then we'll use `distilabel` to generate the
synthetic data. To finish off, we'll push the newly-generated data to a new
Hugging Face dataset and also push the same data to our Argilla instance for
annotation and inspection.

## Generating synthetic data

## Pushing data to Argilla

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


