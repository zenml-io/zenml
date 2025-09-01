"""
Minimal Haystack RAG pipeline for PanAgent.

How it works
------------
1.  We put three short documents into an `InMemoryDocumentStore`.
2.  A BM25 retriever fetches relevant docs for the user's query.
3.  A `PromptBuilder` renders a single template including those docs.
4.  An `OpenAIChatGenerator` produces the final answer.

PanAgent looks for a global variable called ``pipeline`` or ``agent``.  Here we
expose ``pipeline`` so the Haystack adapter will auto-discover it.
"""

from haystack import Document, Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

# --------------------------------------------------------------------------- #
# 1. Create / populate a tiny in-memory document store                         #
# --------------------------------------------------------------------------- #
document_store = InMemoryDocumentStore()
document_store.write_documents(
    [
        Document(
            content="Paris is the capital of France and home to the Eiffel Tower."
        ),
        Document(
            content="Berlin is the capital of Germany and famous for the Brandenburg Gate."
        ),
        Document(
            content="Rome is the capital of Italy and known for the Colosseum."
        ),
    ]
)

# --------------------------------------------------------------------------- #
# 2. Define pipeline components                                               #
# --------------------------------------------------------------------------- #
retriever = InMemoryBM25Retriever(document_store=document_store)

prompt_template = """
Answer the question using ONLY the given documents.

Documents:
{% for doc in documents %}
  • {{ doc.content }}
{% endfor %}

Question: {{question}}

Answer (concise):
"""

prompt_builder = PromptBuilder(template=prompt_template)

llm = OpenAIGenerator(model="gpt-5-nano")

# --------------------------------------------------------------------------- #
# 3. Assemble the pipeline                                                    #
# --------------------------------------------------------------------------- #
pipeline = Pipeline()
pipeline.add_component("retriever", retriever)
pipeline.add_component("prompt_builder", prompt_builder)
pipeline.add_component("llm", llm)

# Connect retriever → prompt_builder.documents and prompt_builder → llm
pipeline.connect("retriever", "prompt_builder.documents")
pipeline.connect("prompt_builder", "llm")

# Warm-up so the first request is fast
pipeline.warm_up()

# --------------------------------------------------------------------------- #
# Example manual invocation (disabled so PanAgent remains the entry-point)    #
# --------------------------------------------------------------------------- #
# if __name__ == "__main__":
#     question = "What city is home to the Eiffel Tower?"
#     result = pipeline.run(
#         {
#             "retriever": {"query": question},
#             "prompt_builder": {"question": question},
#         },
#         include_outputs_from={"llm"},
#     )
#     print(result["llm"]["replies"][0].content)
