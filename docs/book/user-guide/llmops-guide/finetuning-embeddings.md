---
description: Finetune embeddings on custom synthetic data to improve retrieval performance.
---

- why do we finetune embeddings? (what's goal of this section)
- (connect to previous section on reranking)
- what we'll show in this section
  - synthetic data generation with distilabel
  - iterating on data with Argilla
  - finetuning embeddings with Sentence Transformers
  - evaluating finetuned embeddings

Bootstrapping and maintaining production-ready RAG pipelines, requires optimising various components like the LLM, vector database, embeddings and rerankers. Within this notebook we will showcase how you can optimize and maintain your embedding models through synthetic data and human feedback. Besides ZenML, we will do this by using two open source libraries: `argilla` and `distilabel`. Both of these libraries focus optimizing model outputs through improving data quality, however, each one of them take a different approach to tackle the same problem. `distilabel` provides a scalable and reliable approach to distilling knowledge from LLMs by generating synthetic data or providing AI feedback with LLMs as judges. `argilla` enables AI engineers and domain experts to collaborate on data projects by allowing them to organize and explore data through within an interactive and engaging UI. Both libraries can be used individually but they work better together.


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
