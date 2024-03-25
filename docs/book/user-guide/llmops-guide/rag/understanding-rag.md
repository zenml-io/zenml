---
description: Understand the Retrieval-Augmented Generation (RAG) technique and its benefits.
---

# Understanding Retrieval-Augmented Generation (RAG)

RAG helps us address these problems. We can use this technique to leverage the
strengths of both retrieval-based and generation-based models. It uses a
retriever to find relevant documents from a large corpus and then uses a
generator to produce a response based on the retrieved documents. This approach
is particularly useful for tasks that require contextual understanding and
long-form generation, such as question answering, summarization, and dialogue
generation.

RAG helps with the context limitations mentioned above by providing a way to
retrieve relevant documents that can be used to generate a response. This
retrieval step can help ensure that the generated response is grounded in
relevant information, reducing the likelihood of generating incorrect or
inappropriate responses. It also helps with the token limitations by allowing
the generator to focus on a smaller set of relevant documents, rather than
having to process an entire large corpus.

Given the costs associated with running LLMs, RAG can also be more
cost-effective than using a pure generation-based approach, as it allows you to
focus the generator's resources on a smaller set of relevant documents. This can
be particularly important when working with large corpora or when deploying
models to resource-constrained environments.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
