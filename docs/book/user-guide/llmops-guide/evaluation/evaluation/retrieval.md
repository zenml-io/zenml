---
description: See how the retrieval component responds to changes in the pipeline.
---

# Retrieval evaluation

The retrieval component of our RAG pipeline is responsible for finding relevant
documents or document chunks to feed into the generation component. In this
section we'll explore how to evaluate the performance of the retrieval component
of your RAG pipeline. We're checking how accurate the semantic search is, or in
other words how relevant the retrieved documents are to the query.

Our retrieval component takes the incoming query and converts it into a
vector or embedded representation that can be used to search for relevant
documents. We then use this representation to search through a corpus of
documents and retrieve the most relevant ones.

## Manual evaluation using handcrafted queries

The most naive and simple way to check this would be to handcraft some queries
where we know the specific documents needed to answer it. We can then check if
the retrieval component is able to retrieve these documents. This is a manual
evaluation process and can be time-consuming, but it's a good way to get a sense
of how well the retrieval component is working. It can also be useful to target
known edge cases or difficult queries to see how the retrieval component handles
those known scenarios.

Implementing this is pretty simple - you just need to create some queries and
check the retrieved documents. Having tested the basic inference of our RAG
setup quite a bit, there were some clear areas where the retrieval component
could be improved. I looked in our documentation to find some examples where the
information could only be found in a single page and then wrote some queries
that would require the retrieval component to find that page. For example, the
query "How do I get going with the Label Studio integration? What are the first
steps?" would require the retrieval component to find [the Label Studio
integration
page](https://docs.zenml.io/stacks-and-components/component-guide/annotators/label-studio).
You can see other examples in the project code base
[here](https://github.com/zenml-io/zenml-projects/blob/e59ada173c65f79d17025aa48b87fe593229bfe8/llm-complete-guide/steps/eval_retrieval.py#L33-L34).

For the retrieval pipeline, all we have to do is encode the query as a vector
and then query the PostgreSQL database for the most similar vectors. We then
check whether the URL for the document we thought must show up is actually
present in the top n results.

```python
def query_similar_docs(question: str, url_ending: str) -> tuple:
    embedded_question = get_embeddings(question)
    db_conn = get_db_conn()
    top_similar_docs_urls = get_topn_similar_docs(
        embedded_question, db_conn, n=5, only_urls=True
    )
    urls = [url[0] for url in top_similar_docs_urls]  # Unpacking URLs from tuples
    return (question, url_ending, urls)

def test_retrieved_docs_retrieve_best_url(question_doc_pairs: list) -> float:
    total_tests = len(question_doc_pairs)
    failures = 0

    for pair in question_doc_pairs:
        question, url_ending, urls = query_similar_docs(
            pair["question"], pair["url_ending"]
        )
        if all(url_ending not in url for url in urls):
            logging.error(
                f"Failed for question: {question}. Expected URL ending: {url_ending}. Got: {urls}"
            )
            failures += 1

    logging.info(f"Total tests: {total_tests}. Failures: {failures}")
    failure_rate = (failures / total_tests) * 100
    return round(failure_rate, 2)
```

We include some logging so that when running the pipeline locally we can get
some immediate feedback logged to the console.

This functionality can then be packaged up into a ZenML step once we're happy it
does what we need:

```python
@step
def retrieval_evaluation_small() -> Annotated[float, "small_failure_rate_retrieval"]:
    failure_rate = test_retrieved_docs_retrieve_best_url(question_doc_pairs)
    logging.info(f"Retrieval failure rate: {failure_rate}%")
    return failure_rate
```



## Automated evaluation using synthetic generated queries

- synthetic data option (generate synthetic questions and check if the retrieved
  documents are the right ones)


## what we're looking for in the results

## frameworks that can maybe help in this context

just list some resources for people to check out

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
