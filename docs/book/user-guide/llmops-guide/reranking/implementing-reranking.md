---
description: Learn how to implement reranking in ZenML.
---

# Implementing Reranking in ZenML

We already have a working RAG pipeline, so inserting a reranker into the
pipeline is relatively straightforward. The reranker will take the retrieved
documents from the initial retrieval step and reorder them in terms of the query
that was used to retrieve them.

![](/docs/book/.gitbook/assets/reranking-workflow.png)

## How and where to add reranking

We'll use the [`rerankers`](https://github.com/AnswerDotAI/rerankers/) package
to handle the reranking process in our RAG inference pipeline. It's a relatively
low-cost (in terms of technical debt and complexity) and lightweight dependency
to add into our pipeline. It offers an interface to most of the model types that
are commonly used for reranking and means we don't have to worry about the
specifics of each model.

This package provides a `Reranker` abstract class that you can use to define
your own reranker. You can also use the provided implementations to add
reranking to your pipeline. The reranker takes the query and a list of retrieved
documents as input and outputs a reordered list of documents based on the
reranking scores. Here's a toy example:

```python
from rerankers import Reranker

ranker = Reranker('cross-encoder')

texts = [
    "I like to play soccer",
    "I like to play football",
    "War and Peace is a great book"
    "I love dogs",
    "Ginger cats aren't very smart",
    "I like to play basketball",
]

results = ranker.rank(query="What's your favorite sport?", docs=texts)
```

And results will look something like this:

```
RankedResults(
    results=[
        Result(doc_id=5, text='I like to play basketball', score=-0.46533203125, rank=1),
        Result(doc_id=0, text='I like to play soccer', score=-0.7353515625, rank=2),
        Result(doc_id=1, text='I like to play football', score=-0.9677734375, rank=3),
        Result(doc_id=2, text='War and Peace is a great book', score=-5.40234375, rank=4),
        Result(doc_id=3, text='I love dogs', score=-5.5859375, rank=5),
        Result(doc_id=4, text="Ginger cats aren't very smart", score=-5.94921875, rank=6)
    ],
    query="What's your favorite sport?",
    has_scores=True
)
```

We can see that the reranker has reordered the documents based on the reranking
scores, with the most relevant document appearing at the top of the list. The
texts about sport are at the top and the less relevant ones about animals are
down at the bottom.

We specified that we want a `cross-encoder` reranker, but you can also use other
reranker models from the Hugging Face Hub, use API-driven reranker models (from
Jina or Cohere, for example), or even define your own reranker model. Read
[their documentation](https://github.com/AnswerDotAI/rerankers/) to see how to
use these different configurations.

In our case, we can simply add a helper function that can optionally be invoked
when we want to use the reranker:

```python

def rerank_documents(
    query: str, documents: List[Tuple], reranker_model: str = "flashrank"
) -> List[Tuple[str, str]]:
    """Reranks the given documents based on the given query."""
    ranker = Reranker(reranker_model)
    docs_texts = [f"{doc[0]} PARENT SECTION: {doc[2]}" for doc in documents]
    results = ranker.rank(query=query, docs=docs_texts)
    # pair the texts with the original urls in `documents`
    # `documents` is a tuple of (content, url)
    # we want the urls to be returned
    reranked_documents_and_urls = []
    for result in results.results:
        # content is a `rerankers` Result object
        index_val = result.doc_id
        doc_text = result.text
        doc_url = documents[index_val][1]
        reranked_documents_and_urls.append((doc_text, doc_url))
    return reranked_documents_and_urls
```

This function takes a query and a list of documents (each document is a tuple of
content and URL) and reranks the documents based on the query. It returns a list
of tuples, where each tuple contains the reranked document text and the URL of
the original document. We use the `flashrank` model from the `rerankers` package
by default as it appeared to be a good choice for our use case during
development.

This function then gets used in tests in the following way:

```python
def query_similar_docs(
    question: str,
    url_ending: str,
    use_reranking: bool = False,
    returned_sample_size: int = 5,
) -> Tuple[str, str, List[str]]:
    """Query similar documents for a given question and URL ending."""
    embedded_question = get_embeddings(question)
    db_conn = get_db_conn()
    num_docs = 20 if use_reranking else returned_sample_size
    # get (content, url) tuples for the top n similar documents
    top_similar_docs = get_topn_similar_docs(
        embedded_question, db_conn, n=num_docs, include_metadata=True
    )

    if use_reranking:
        reranked_docs_and_urls = rerank_documents(question, top_similar_docs)[
            :returned_sample_size
        ]
        urls = [doc[1] for doc in reranked_docs_and_urls]
    else:
        urls = [doc[1] for doc in top_similar_docs]  # Unpacking URLs

    return (question, url_ending, urls)
```

We get the embeddings for the question being passed into the function and
connect to our PostgreSQL database. If we're using reranking, we get the top 20
documents similar to our query and rerank them using the `rerank_documents`
helper function. We then extract the URLs from the reranked documents and return
them. Note that we only return 5 URLs, but in the case of reranking we get a
larger number of documents and URLs back from the database to pass to our
reranker, but in the end we always choose the top five reranked documents to
return.

Now that we've added reranking to our pipeline, we can evaluate the performance
of our reranker and see how it affects the quality of the retrieved documents.

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/)
repository and for this section, particularly [the `eval_retrieval.py` file](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/steps/eval_retrieval.py).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
