---
description: Store embeddings in a vector database for efficient retrieval.
---

# Storing Embeddings in a Vector Database

The process of generating the embeddings doesn't take too long, especially if
the machine on which the step is running has a GPU, but it's still not something
we want to do every time we need to retrieve a document. Instead, we can store
the embeddings in a vector database, which allows us to quickly retrieve the
most relevant chunks based on their similarity to the query.

For the purposes of this guide, we'll use PostgreSQL as our vector database.
This is a popular choice for storing embeddings, as it provides a scalable and
efficient way to store and retrieve high-dimensional vectors. However, you can
use any vector database that supports high-dimensional vectors. If you want to
explore a list of possible options, [this is a good
website](https://superlinked.com/vector-db-comparison/) to compare different
options.

{% hint style="info" %}
For more information on how to set up a PostgreSQL database to follow along with
this guide, please see the instructions in the repository which show how to set
up a PostgreSQL database using Supabase.
{% endhint %}

Since PostgreSQL is such a standard kind of database, we can use known and
minimal packages to connect and to interact with it. We can use the `psycopg2`
package to connect and then raw SQL statements to interact with the database.

The code for the step is fairly simple:

```python
from zenml import step

@step
def index_generator(
    embeddings: np.ndarray,
    documents: List[str],
) -> None:
    """Generates an index for the given embeddings and documents."""
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
                        tokens INTEGER,
                        embedding VECTOR({EMBEDDING_DIMENSIONALITY})
                        );
                        """
            cur.execute(table_create_command)
            conn.commit()

            register_vector(conn)

            # Insert data only if it doesn't already exist
            for i, doc in enumerate(documents):
                content = doc
                tokens = len(
                    content.split()
                )  # Approximate token count based on word count
                embedding = embeddings[i].tolist()

                cur.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE content = %s",
                    (content,),
                )
                count = cur.fetchone()[0]
                if count == 0:
                    cur.execute(
                        "INSERT INTO embeddings (content, tokens, embedding) VALUES (%s, %s, %s)",
                        (content, tokens, embedding),
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

- connect to the database
- create the `vector` extension if it doesn't already exist (this is to enable
  the vector data type in PostgreSQL)
- create the `embeddings` table if it doesn't exist
- insert the embeddings and documents into the table
- calculate the index parameters according to best practices
- create an index on the embeddings

Note that we're inserting the documents into the embeddings table as well as the
embeddings themselves. This is so that we can retrieve the documents based on
their embeddings later on. It also helps with debugging from within the Supabase
interface or wherever else we're examining the contents of the database.

![The Supabase editor interface](/docs/book/.gitbook/assets/supabase-editor-interface.png)

Deciding when to update your embeddings is a separate discussion and depends on
the specific use case. If your data is frequently changing, and the changes are
significant, you might want to fully reset the embeddings with each update. In
other cases, you might just want to add new documents and embeddings into the
database because the changes are minor or infrequent. In the code above, we
choose to only add new embeddings if they don't already exist in the database.

We also generate an index


 and update the index store. This is a crucial step in the RAG pipeline, as it
ensures that the retriever has access to the most up-to-date and relevant
documents. The preprocessing step can include a variety of tasks, such as
cleaning and normalizing the text, extracting relevant features, and updating
the index store with the new documents.

For the purposes of simplicity we show this using an in-memory vector database
(the FAISS vector database). This is a simple way to index documents and is
suitable for small to medium-sized corpora. For larger corpora, you would want
to use a more scalable solution, most likely deployed on a cloud provider.

```python
from typing_extensions import Annotated
from typing import List

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
)
from langchain.schema.vectorstore import VectorStore
from langchain.vectorstores.faiss import FAISS
from zenml import step, log_artifact_metadata


@step
def index_generator(
    documents: List[Document],
) -> Annotated[VectorStore, "vector_store"]:
    """Generates a vector store from a list of documents."""
    embeddings = OpenAIEmbeddings()

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    compiled_texts = text_splitter.split_documents(documents)

    log_artifact_metadata(
        artifact_name="vector_store",
        metadata={
            "embedding_type": "OpenAIEmbeddings",
            "vector_store_type": "FAISS",
        },
    )

    return FAISS.from_documents(compiled_texts, embeddings)
```

Before data is ingested into the vector store, it is split into chunks of 1000
characters with a 0 character overlap. This is a simple way to ensure that the
documents are split into manageable chunks that can be processed by the
retriever and generator models. The vector store is then generated from the
compiled texts using the OpenAIEmbeddings and FAISS vector store types.
Adjusting the chunk size and chunk overlap are both parameters that you might
want to experiment with to see how they affect the performance of your RAG
pipeline.

We make sure to log the metadata for the artifact, including the embedding type
and the vector store type. This will be visible in the dashboard and can be
useful for debugging and understanding the pipeline. It also allows you to track
the evolution of the pipeline over time.

So now we have a vector store that we can use to retrieve documents. We
populated the index store with documents that are meaningful to our use case so
that we can retrieve chunks that are relevant to questions passed into our RAG
pipeline.







<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
