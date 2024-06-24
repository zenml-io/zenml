---
description: Understand how reranking works.
---

## What is reranking?

Reranking is the process of refining the initial ranking of documents retrieved
by a retrieval system. In the context of Retrieval-Augmented Generation (RAG),
reranking plays a crucial role in improving the relevance and quality of the
retrieved documents that are used to generate the final output.

The initial retrieval step in RAG typically uses a sparse retrieval method, such
as BM25 or TF-IDF, to quickly find a set of potentially relevant documents based
on the input query. However, these methods rely on lexical matching and may not
capture the semantic meaning or context of the query effectively.

Rerankers, on the other hand, are designed to reorder the retrieved documents by
considering additional features, such as semantic similarity, relevance scores,
or domain-specific knowledge. They aim to push the most relevant and informative
documents to the top of the list, ensuring that the LLM has access to the best
possible context for generating accurate and coherent responses.

## Types of Rerankers

There are different types of rerankers that can be used in RAG, each with its
own strengths and trade-offs:

1. **Cross-Encoders**: Cross-encoders are a popular choice for reranking in RAG.
   They take the concatenated query and document as input and output a relevance
   score. Examples include BERT-based models fine-tuned for passage ranking
   tasks. Cross-encoders can capture the interaction between the query and
   document effectively but are computationally expensive.

2. **Bi-Encoders**: Bi-encoders, also known as dual encoders, use separate
   encoders for the query and document. They generate embeddings for the query
   and document independently and then compute the similarity between them.
   Bi-encoders are more efficient than cross-encoders but may not capture the
   query-document interaction as effectively.

3. **Lightweight Models**: Lightweight rerankers, such as distilled models or
   small transformer variants, aim to strike a balance between effectiveness and
   efficiency. They are faster and have a smaller footprint compared to large
   cross-encoders, making them suitable for real-time applications.

## Benefits of Reranking in RAG

Reranking offers several benefits in the context of RAG:

1. **Improved Relevance**: By considering additional features and scores,
   rerankers can identify the most relevant documents for a given query,
   ensuring that the LLM has access to the most informative context for
   generating accurate responses.

2. **Semantic Understanding**: Rerankers can capture the semantic meaning and
   context of the query and documents, going beyond simple keyword matching.
   This enables the retrieval of documents that are semantically similar to the
   query, even if they don't contain exact keyword matches.

3. **Domain Adaptation**: Rerankers can be fine-tuned on domain-specific data to
   incorporate domain knowledge and improve performance in specific verticals or
   industries.

4. **Personalization**: Rerankers can be personalized based on user preferences,
   historical interactions, or user profiles, enabling the retrieval of
   documents that are more tailored to individual users' needs.

In the next section, we'll dive into how to implement reranking in ZenML and
integrate it into your RAG inference pipeline.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
