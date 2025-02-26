---
description: Use your RAG components to generate responses to prompts.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Simple RAG Inference

Now that we have our index store, we can use it to make queries based on the
documents in the index store. We use some utility functions to make this happen
but no external libraries are needed beyond an interface to the index store as
well as the LLM itself.

![](/docs/book/.gitbook/assets/rag-stage-4.png)

If you've been following along with the guide, you should have some documents
ingested already and you can pass a query in as a flag to the Python command
used to run the pipeline:

```bash
python run.py --rag-query "how do I use a custom materializer inside my own zenml 
steps? i.e. how do I set it? inside the @step decorator?" --model=gpt4
```

![](/docs/book/.gitbook/assets/rag-inference.png)

This inference query itself is not a ZenML pipeline, but rather a function call
which uses the outputs and components of our pipeline to generate the response.
For a more complex inference setup, there might be even more going on here, but
for the purposes of this initial guide we will keep it simple.

Bringing everything together, the code for the inference pipeline is as follows:

```python
def process_input_with_retrieval(
    input: str, model: str = OPENAI_MODEL, n_items_retrieved: int = 5
) -> str:
    delimiter = "```"

    # Step 1: Get documents related to the user input from database
    related_docs = get_topn_similar_docs(
        get_embeddings(input), get_db_conn(), n=n_items_retrieved
    )

    # Step 2: Get completion from OpenAI API
    # Set system message to help set appropriate tone and context for model
    system_message = f"""
    You are a friendly chatbot. \
    You can answer questions about ZenML, its features and its use cases. \
    You respond in a concise, technically credible tone. \
    You ONLY use the context from the ZenML documentation to provide relevant
    answers. \
    You do not make up answers or provide opinions that you don't have
    information to support. \
    If you are unsure or don't know, just say so. \
    """

    # Prepare messages to pass to model
    # We use a delimiter to help the model understand the where the user_input
    # starts and ends

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"{delimiter}{input}{delimiter}"},
        {
            "role": "assistant",
            "content": f"Relevant ZenML documentation: \n"
            + "\n".join(doc[0] for doc in related_docs),
        },
    ]
    logger.debug("CONTEXT USED\n\n", messages[2]["content"], "\n\n")
    return get_completion_from_messages(messages, model=model)
```

For the `get_topn_similar_docs` function, we use the embeddings generated from
the documents in the index store to find the most similar documents to the
query:

```python
def get_topn_similar_docs(
    query_embedding: List[float],
    conn: psycopg2.extensions.connection,
    n: int = 5,
    include_metadata: bool = False,
    only_urls: bool = False,
) -> List[Tuple]:
    embedding_array = np.array(query_embedding)
    register_vector(conn)
    cur = conn.cursor()

    if include_metadata:
        cur.execute(
            f"SELECT content, url FROM embeddings ORDER BY embedding <=> %s LIMIT {n}",
            (embedding_array,),
        )
    elif only_urls:
        cur.execute(
            f"SELECT url FROM embeddings ORDER BY embedding <=> %s LIMIT {n}",
            (embedding_array,),
        )
    else:
        cur.execute(
            f"SELECT content FROM embeddings ORDER BY embedding <=> %s LIMIT {n}",
            (embedding_array,),
        )

    return cur.fetchall()
```

Luckily we are able to get these similar documents using a function in
[`pgvector`](https://github.com/pgvector/pgvector), a plugin package for
PostgreSQL: `ORDER BY embedding <=> %s` orders the documents by their similarity
to the query embedding. This is a very efficient way to get the most relevant
documents to the query and is a great example of how we can leverage the power
of the database to do the heavy lifting for us.

For the `get_completion_from_messages` function, we use
[`litellm`](https://github.com/BerriAI/litellm) as a universal interface that
allows us to use lots of different LLMs. As you can see above, the model is able
to synthesize the documents it has been given and provide a response to the
query.

```python
def get_completion_from_messages(
    messages, model=OPENAI_MODEL, temperature=0.4, max_tokens=1000
):
    """Generates a completion response from the given messages using the specified model."""
    model = MODEL_NAME_MAP.get(model, model)
    completion_response = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion_response.choices[0].message.content
```

We're using `litellm` because it makes sense not to have to implement separate
functions for each LLM we might want to use. The pace of development in the
field is such that you will want to experiment with new LLMs as they come out,
and `litellm` gives you the flexibility to do that without having to rewrite
your code.

We've now completed a basic RAG inference pipeline that uses the embeddings
generated by the pipeline to retrieve the most relevant chunks of text based on
a given query. We can inspect the various components of the pipeline to see how
they work together to provide a response to the query. This gives us a solid
foundation to move onto more complex RAG pipelines and to look into how we might
improve this. The next section will cover how to improve retrieval by finetuning
the embeddings generated by the pipeline. This will boost our performance in
situations where we have a large volume of documents and also when the documents
are potentially very different from the training data that was used for the
embeddings.

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide)
repository and for this section, particularly [the `llm_utils.py` file](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/utils/llm_utils.py).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
