---
description: Store embeddings in a vector database for efficient retrieval.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Storing embeddings in a vector database

The process of generating the embeddings doesn't take too long, especially if the machine on which the step is running has a GPU, but it's still not something we want to do every time we need to retrieve a document. Instead, we can store the embeddings in a vector database, which allows us to quickly retrieve the most relevant chunks based on their similarity to the query.

![](../../../.gitbook/assets/rag-stage-3.png)

For the purposes of this guide, we'll use PostgreSQL as our vector database. This is a popular choice for storing embeddings, as it provides a scalable and efficient way to store and retrieve high-dimensional vectors. However, you can use any vector database that supports high-dimensional vectors. If you want to explore a list of possible options, [this is a good website](https://superlinked.com/vector-db-comparison/) to compare different options.

{% hint style="info" %}
For more information on how to set up a PostgreSQL database to follow along with this guide, please [see the instructions in the repository](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide) which show how to set up a PostgreSQL database using Supabase.
{% endhint %}

Since PostgreSQL is a well-known and battle-tested database, we can use known and minimal packages to connect and to interact with it. We can use the [`psycopg2`](https://www.psycopg.org/docs/) package to connect and then raw SQL statements to interact with the database.

The code for the step is fairly simple:

```python
from zenml import step

@step
def index_generator(
    documents: List[Document],
) -> None:
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            # Install pgvector if not already installed
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()

            # Create the embeddings table if it doesn't exist
            table_create_command = f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        token_count INTEGER,
                        embedding VECTOR({EMBEDDING_DIMENSIONALITY}),
                        filename TEXT,
                        parent_section TEXT,
                        url TEXT
                        );
                        """
            cur.execute(table_create_command)
            conn.commit()

            register_vector(conn)

            # Insert data only if it doesn't already exist
            for doc in documents:
                content = doc.page_content
                token_count = doc.token_count
                embedding = doc.embedding.tolist()
                filename = doc.filename
                parent_section = doc.parent_section
                url = doc.url

                cur.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE content = %s",
                    (content,),
                )
                count = cur.fetchone()[0]
                if count == 0:
                    cur.execute(
                        "INSERT INTO embeddings (content, token_count, embedding, filename, parent_section, url) VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            content,
                            token_count,
                            embedding,
                            filename,
                            parent_section,
                            url,
                        ),
                    )
                    conn.commit()

            cur.execute("SELECT COUNT(*) as cnt FROM embeddings;")
            num_records = cur.fetchone()[0]
            logger.info(f"Number of vector records in table: {num_records}")

            # calculate the index parameters according to best practices
            num_lists = max(num_records / 1000, 10)
            if num_records > 1000000:
                num_lists = math.sqrt(num_records)

            # use the cosine distance measure, which is what we'll later use for querying
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS embeddings_idx ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = {num_lists});"
            )
            conn.commit()

    except Exception as e:
        logger.error(f"Error in index_generator: {e}")
        raise
    finally:
        if conn:
            conn.close()
```

We use some utility functions, but what we do here is:

* connect to the database
* create the `vector` extension if it doesn't already exist (this is to enable the vector data type in PostgreSQL)
* create the `embeddings` table if it doesn't exist
* insert the embeddings and documents into the table
* calculate the index parameters according to best practices
* create an index on the embeddings

Note that we're inserting the documents into the embeddings table as well as the embeddings themselves. This is so that we can retrieve the documents based on their embeddings later on. It also helps with debugging from within the Supabase interface or wherever else we're examining the contents of the database.

![The Supabase editor interface](../../../.gitbook/assets/supabase-editor-interface.png)

Deciding when to update your embeddings is a separate discussion and depends on the specific use case. If your data is frequently changing, and the changes are significant, you might want to fully reset the embeddings with each update. In other cases, you might just want to add new documents and embeddings into the database because the changes are minor or infrequent. In the code above, we choose to only add new embeddings if they don't already exist in the database.

{% hint style="info" %}
Depending on the size of your dataset and the number of embeddings you're storing, you might find that running this step on a CPU is too slow. In that case, you should ensure that this step runs on a GPU-enabled machine to speed up the process. You can do this with ZenML by using a step operator that runs on a GPU-enabled machine. See [the docs here](../../../component-guide/step-operators/README.md) for more on how to set this up.
{% endhint %}

We also generate an index for the embeddings using the `ivfflat` method with the `vector_cosine_ops` operator. This is a common method for indexing high-dimensional vectors in PostgreSQL and is well-suited for similarity search using cosine distance. The number of lists is calculated based on the number of records in the table, with a minimum of 10 lists and a maximum of the square root of the number of records. This is a good starting point for tuning the index parameters, but you might want to experiment with different values to see how they affect the performance of your RAG pipeline.

Now that we have our embeddings stored in a vector database, we can move on to the next step in the pipeline, which is to retrieve the most relevant documents based on a given query. This is where the real magic of the RAG pipeline comes into play, as we can use the embeddings to quickly retrieve the most relevant chunks of text based on their similarity to the query. This allows us to build a powerful and efficient question-answering system that can provide accurate and relevant responses to user queries in real-time.

## Code Example

To explore the full code, visit the [Complete Guide](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide) repository. The logic for storing the embeddings in PostgreSQL can be found [here](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide/steps/populate\_index.py).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
