---
description: Generate embeddings to improve retrieval performance.
---

# Generating Embeddings for Retrieval

In this section, we'll explore how to generate embeddings for your data to
improve retrieval performance in your RAG pipeline. Embeddings are a crucial
part of the retrieval mechanism in RAG, as they represent the data in a
high-dimensional space where similar items are closer together. By generating
embeddings for your data, you can enhance the retrieval capabilities of your RAG
pipeline and provide more accurate and relevant responses to user queries.

![](/docs/book/.gitbook/assets/rag-stage-2.png)

{% hint style="info" %} Embeddings are vector representations of data that capture the semantic
meaning and context of the data in a high-dimensional space. They are generated
using machine learning models, such as word embeddings or sentence embeddings,
that learn to encode the data in a way that preserves its underlying structure
and relationships. Embeddings are commonly used in natural language processing
(NLP) tasks, such as text classification, sentiment analysis, and information
retrieval, to represent textual data in a format that is suitable for
computational processing. {% endhint %}

The whole purpose of the embeddings is to allow us to quickly find the small
chunks that are most relevant to our input query at inference time. An even
simpler way of doing this would be to just to search for some keywords in the
query and hope that they're also represented in the chunks. However, this
approach is not very robust and may not work well for more complex queries or
longer documents. By using embeddings, we can capture the semantic meaning and
context of the data and retrieve the most relevant chunks based on their
similarity to the query.

We're using the [`sentence-transformers`](https://www.sbert.net/) library to generate embeddings for our
data. This library provides pre-trained models for generating sentence
embeddings that capture the semantic meaning of the text. It's an open-source
library that is easy to use and provides high-quality embeddings for a wide
range of NLP tasks.

```python
from typing import Annotated, List
import numpy as np
from sentence_transformers import SentenceTransformer
from structures import Document
from zenml import ArtifactConfig, log_artifact_metadata, step

@step
def generate_embeddings(
    split_documents: List[Document],
) -> Annotated[
    List[Document], ArtifactConfig(name="documents_with_embeddings")
]:
    try:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")

        log_artifact_metadata(
            artifact_name="embeddings",
            metadata={
                "embedding_type": "sentence-transformers/all-MiniLM-L12-v2",
                "embedding_dimensionality": 384,
            },
        )

        document_texts = [doc.page_content for doc in split_documents]
        embeddings = model.encode(document_texts)

        for doc, embedding in zip(split_documents, embeddings):
            doc.embedding = embedding

        return split_documents
    except Exception as e:
        logger.error(f"Error in generate_embeddings: {e}")
        raise
```

We update the `Document` Pydantic model to include an `embedding` attribute that
stores the embedding generated for each document. This allows us to associate
the embeddings with the corresponding documents and use them for retrieval
purposes in the RAG pipeline.

There are smaller embeddings models if we cared a lot about speed, and larger
ones (with more dimensions) if we wanted to boost our ability to retrieve more
relevant chunks. [The model we're using
here](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2) is on the
smaller side, but it should work well for our use case. The embeddings generated
by this model have a dimensionality of 384, which means that each embedding is
represented as a 384-dimensional vector in the high-dimensional space.

We can use dimensionality reduction functionality in
[`umap`](https://umap-learn.readthedocs.io/) and
[`scikit-learn`](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html#sklearn-manifold-tsne)
to represent the 384 dimensions of our embeddings in two-dimensional space. This
allows us to visualize the embeddings and see how similar chunks are clustered
together based on their semantic meaning and context. We can also use this
visualization to identify patterns and relationships in the data that can help
us improve the retrieval performance of our RAG pipeline. It's worth trying both
UMAP and t-SNE to see which one works best for our use case since they both have
somewhat different representations of the data and reduction algorithms, as
you'll see.

```python
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import numpy as np
from sklearn.manifold import TSNE
import umap
from zenml.client import Client

artifact = Client().get_artifact_version('EMBEDDINGS_ARTIFACT_UUID_GOES_HERE')
embeddings = artifact.load()


embeddings = np.array([doc.embedding for doc in documents])
parent_sections = [doc.parent_section for doc in documents]

# Get unique parent sections
unique_parent_sections = list(set(parent_sections))

# Tol color palette
tol_colors = [
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#BBBBBB",
]

# Create a colormap with Tol colors
tol_colormap = ListedColormap(tol_colors)

# Assign colors to each unique parent section
section_colors = tol_colors[: len(unique_parent_sections)]

# Create a dictionary mapping parent sections to colors
section_color_dict = dict(zip(unique_parent_sections, section_colors))

# Dimensionality reduction using t-SNE
def tsne_visualization(embeddings, parent_sections):
    tsne = TSNE(n_components=2, random_state=42)
    embeddings_2d = tsne.fit_transform(embeddings)

    plt.figure(figsize=(8, 8))
    for section in unique_parent_sections:
        if section in section_color_dict:
            mask = [section == ps for ps in parent_sections]
            plt.scatter(
                embeddings_2d[mask, 0],
                embeddings_2d[mask, 1],
                c=[section_color_dict[section]],
                label=section,
            )

    plt.title("t-SNE Visualization")
    plt.legend()
    plt.show()


# Dimensionality reduction using UMAP
def umap_visualization(embeddings, parent_sections):
    umap_2d = umap.UMAP(n_components=2, random_state=42)
    embeddings_2d = umap_2d.fit_transform(embeddings)

    plt.figure(figsize=(8, 8))
    for section in unique_parent_sections:
        if section in section_color_dict:
            mask = [section == ps for ps in parent_sections]
            plt.scatter(
                embeddings_2d[mask, 0],
                embeddings_2d[mask, 1],
                c=[section_color_dict[section]],
                label=section,
            )

    plt.title("UMAP Visualization")
    plt.legend()
    plt.show()
```

![UMAP visualization of the ZenML documentation chunks as embeddings](/docs/book/.gitbook/assets/umap.png)
![t-SNE visualization of the ZenML documentation chunks as embeddings](/docs/book/.gitbook/assets/tsne.png)

In this stage, we have utilized the 'parent directory', which we had previously
stored in the vector store as an additional attribute, as a means to color the
values. This approach allows us to gain some insight into the semantic space
inherent in our data. It demonstrates that you can visualize the embeddings and
observe how similar chunks are grouped together based on their semantic meaning
and context.

So this step iterates through all the chunks and generates embeddings
representing each piece of text. These embeddings are then stored as an artifact
in the ZenML artifact store as a NumPy array. We separate this generation from
the point where we upload those embeddings to the vector database to keep the
pipeline modular and flexible; in the future we might want to use a different
vector database so we can just swap out the upload step without having to
re-generate the embeddings.

In the next section, we'll explore how to store these embeddings in a vector
database to enable fast and efficient retrieval of relevant chunks at inference
time.

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide)
repository. The embeddings generation step can be found
[here](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide/steps/populate_index.py).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
