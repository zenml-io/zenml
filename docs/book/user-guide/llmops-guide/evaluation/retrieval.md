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

![](/docs/book/.gitbook/assets/retrieval-eval-manual.png)

Implementing this is pretty simple - you just need to create some queries and
check the retrieved documents. Having tested the basic inference of our RAG
setup quite a bit, there were some clear areas where the retrieval component
could be improved. I looked in our documentation to find some examples where the
information could only be found in a single page and then wrote some queries
that would require the retrieval component to find that page. For example, the
query "How do I get going with the Label Studio integration? What are the first
steps?" would require the retrieval component to find [the Label Studio integration page](https://docs.zenml.io/stacks/annotators/label-studio).
Some of the other examples used are:

| Question | URL Ending |
|----------|------------|
| How do I get going with the Label Studio integration? What are the first steps? | stacks-and-components/component-guide/annotators/label-studio |
| How can I write my own custom materializer? | user-guide/advanced-guide/data-management/handle-custom-data-types |
| How do I generate embeddings as part of a RAG pipeline when using ZenML? | user-guide/llmops-guide/rag-with-zenml/embeddings-generation |
| How do I use failure hooks in my ZenML pipeline? | user-guide/advanced-guide/pipelining-features/use-failure-success-hooks |
| Can I deploy ZenML self-hosted with Helm? How do I do it? | deploying-zenml/zenml-self-hosted/deploy-with-helm |

For the retrieval pipeline, all we have to do is encode the query as a vector
and then query the PostgreSQL database for the most similar vectors. We then
check whether the URL for the document we thought must show up is actually
present in the top `n` results.

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

We got a 20% failure rate on the first run of this test, which was a good sign
that the retrieval component could be improved. We only had 5 test cases, so
this was just a starting point. In reality, you'd want to keep adding more test
cases to cover a wider range of scenarios. You'll discover these failure cases
as you use the system more and more, so it's a good idea to keep a record of
them and add them to your test suite.

You'd also want to examine the logs to see exactly which query failed. In our
case, checking the logs in the ZenML dashboard, we find the following:

```
Failed for question: How do I generate embeddings as part of a RAG 
pipeline when using ZenML?. Expected URL ending: user-guide/llmops-guide/
rag-with-zenml/embeddings-generation. Got: ['https://docs.zenml.io/user-guide/
llmops-guide/rag-with-zenml/data-ingestion', 'https://docs.zenml.io/user-guide/
llmops-guide/rag-with-zenml/understanding-rag', 'https://docs.zenml.io/v/docs/
user-guide/advanced-guide/data-management/handle-custom-data-types', 'https://docs.
zenml.io/user-guide/llmops-guide/rag-with-zenml', 'https://docs.zenml.io/v/docs/
user-guide/llmops-guide/rag-with-zenml']
```

We can maybe take a look at those documents to see why they were retrieved and
not the one we expected. This is a good way to iteratively improve the retrieval
component.

## Automated evaluation using synthetic generated queries

For a broader evaluation we can examine a larger number of queries to check the
retrieval component's performance. We do this by using an LLM to generate
synthetic data. In our case we take the text of each document chunk and pass it
to an LLM, telling it to generate a question. 

![](/docs/book/.gitbook/assets/retrieval-eval-automated.png)

For example, given the text:

```
zenml orchestrator connect ${ORCHESTRATOR\_NAME} -iHead on over to our docs to 
learn more about orchestrators and how to configure them. Container Registry export 
CONTAINER\_REGISTRY\_NAME=gcp\_container\_registry zenml container-registry register $
{CONTAINER\_REGISTRY\_NAME} --flavor=gcp --uri=<GCR-URI> # Connect the GCS 
orchestrator to the target gcp project via a GCP Service Connector zenml 
container-registry connect ${CONTAINER\_REGISTRY\_NAME} -i Head on over to our docs to 
learn more about container registries and how to configure them. 7) Create Stack 
export STACK\_NAME=gcp\_stack zenml stack register ${STACK\_NAME} -o $
{ORCHESTRATOR\_NAME} \\ a ${ARTIFACT\_STORE\_NAME} -c ${CONTAINER\_REGISTRY\_NAME} 
--set In case you want to also add any other stack components to this stack, feel free 
to do so. And you're already done! Just like that, you now have a fully working GCP 
stack ready to go. Feel free to take it for a spin by running a pipeline on it. 
Cleanup If you do not want to use any of the created resources in the future, simply 
delete the project you created. gcloud project delete <PROJECT\_ID\_OR\_NUMBER> <!-- 
For scarf --> <figure><img alt="ZenML Scarf" 
referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?
x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure> PreviousScale compute to the 
cloud NextConfiguring ZenML Last updated 2 days ago
```

we might get the question:

```
How do I create and configure a GCP stack in ZenML using an 
orchestrator, container registry, and stack components, and how 
do I delete the resources when they are no longer needed?
```

If we generate questions for all of our chunks, we can then use these
question-chunk pairs to evaluate the retrieval component. We pass the generated
query to the retrieval component and then we check if the URL for the original
document is in the top `n` results.

To generate the synthetic queries we can use the following code:

```python
from typing import List

from litellm import completion
from structures import Document
from zenml import step

LOCAL_MODEL = "ollama/mixtral"


def generate_question(chunk: str, local: bool = False) -> str:
    model = LOCAL_MODEL if local else "gpt-3.5-turbo"
    response = completion(
        model=model,
        messages=[
            {
                "content": f"This is some text from ZenML's documentation. Please generate a question that can be asked about this text: `{chunk}`",
                "role": "user",
            }
        ],
        api_base="http://localhost:11434" if local else None,
    )
    return response.choices[0].message.content


@step
def generate_questions_from_chunks(
    docs_with_embeddings: List[Document],
    local: bool = False,
) -> List[Document]:
    for doc in docs_with_embeddings:
        doc.generated_questions = [generate_question(doc.page_content, local)]

    assert all(doc.generated_questions for doc in docs_with_embeddings)

    return docs_with_embeddings
```

As you can see, we're using [`litellm`](https://docs.litellm.ai/) again as the
wrapper for the API calls. This allows us to switch between using a cloud LLM
API (like OpenAI's GPT3.5 or 4) and a local LLM (like a quantized version of
Mistral AI's Mixtral made available with [Ollama](https://ollama.com/). This has
a number of advantages:

- you keep your costs down by using a local model
- you can iterate faster by not having to wait for API calls
- you can use the same code for both local and cloud models

For some tasks you'll want to use the best model your budget can afford, but for
this task of question generation we're fine using a local and slightly less
capable model. Even better is that it'll be much faster to generate the
questions, especially using the basic setup we have here.

To give you an indication of how long this process takes, generating 1800+
questions from an equivalent number of documentation chunks took a little over
45 minutes using the local model on a GPU-enabled machine with Ollama.

![](/docs/book/.gitbook/assets/hf-qa-embedding-questions.png)

You can [view the generated
dataset](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions) on
the Hugging Face Hub
[here](https://huggingface.co/datasets/zenml/rag_qa_embedding_questions). This
dataset contains the original document chunks, the generated questions, and the
URL reference for the original document.

Once we have the generated questions, we can then pass them to the retrieval
component and check the results. For convenience we load the data from the
Hugging Face Hub and then pass it to the retrieval component for evaluation. We
shuffle the data and select a subset of it to speed up the evaluation process,
but for a more thorough evaluation you could use the entire dataset. (The best
practice of keeping a separate set of data for evaluation purposes is also
recommended here, though we're not doing that in this example.)

```python
@step
def retrieval_evaluation_full(
    sample_size: int = 50,
) -> Annotated[float, "full_failure_rate_retrieval"]:
    dataset = load_dataset("zenml/rag_qa_embedding_questions", split="train")

    sampled_dataset = dataset.shuffle(seed=42).select(range(sample_size))

    total_tests = len(sampled_dataset)
    failures = 0

    for item in sampled_dataset:
        generated_questions = item["generated_questions"]
        question = generated_questions[
            0
        ]  # Assuming only one question per item
        url_ending = item["filename"].split("/")[
            -1
        ]  # Extract the URL ending from the filename

        _, _, urls = query_similar_docs(question, url_ending)

        if all(url_ending not in url for url in urls):
            logging.error(
                f"Failed for question: {question}. Expected URL ending: {url_ending}. Got: {urls}"
            )
            failures += 1

    logging.info(f"Total tests: {total_tests}. Failures: {failures}")
    failure_rate = (failures / total_tests) * 100
    return round(failure_rate, 2)
```

When we run this as part of the evaluation pipeline, we get a 16% failure rate
which again tells us that we're doing pretty well but that there is room for
improvement. As a baseline, this is a good starting point. We can then iterate
on the retrieval component to improve its performance. 

To take this further, there are a number of ways it might be improved:

- **More diverse question generation**: The current question generation approach
  uses a single prompt to generate questions based on the document chunks. You
  could experiment with different prompts or techniques to generate a wider
  variety of questions that test the retrieval component more thoroughly. For
  example, you could prompt the LLM to generate questions of different types
  (factual, inferential, hypothetical, etc.) or difficulty levels.
- **Semantic similarity metrics**: In addition to checking if the expected URL
  is retrieved, you could calculate semantic similarity scores between the query
  and the retrieved documents using metrics like cosine similarity. This would
  give you a more nuanced view of retrieval performance beyond just binary
  success/failure. You could track average similarity scores and use them as a
  target metric to improve.
- **Comparative evaluation**: Test out different retrieval approaches (e.g.
  different embedding models, similarity search algorithms, etc.) and compare
  their performance on the same set of queries. This would help identify the
  strengths and weaknesses of each approach.
- **Error analysis**: Do a deeper dive into the failure cases to understand
  patterns and potential areas for improvement. Are certain types of questions
  consistently failing? Are there common characteristics among the documents
  that aren't being retrieved properly? Insights from error analysis can guide
  targeted improvements to the retrieval component.

To wrap up, the retrieval evaluation process we've walked through - from manual
spot-checking with carefully crafted queries to automated testing with synthetic
question-document pairs - has provided a solid baseline understanding of our
retrieval component's performance. The failure rates of 20% on our handpicked
test cases and 16% on a larger sample of generated queries highlight clear room
for improvement, but also validate that our semantic search is generally
pointing in the right direction.

Going forward, we have a rich set of options to refine and upgrade our
evaluation approach. Generating a more diverse array of test questions,
leveraging semantic similarity metrics for a nuanced view beyond binary
success/failure, performing comparative evaluations of different retrieval
techniques, and conducting deep error analysis on failure cases - all of these
avenues promise to yield valuable insights. As our RAG pipeline grows to handle
more complex and wide-ranging queries, continued investment in comprehensive
retrieval evaluation will be essential to ensure we're always surfacing the most
relevant information.

Before we start working to improve or tweak our retrieval based on these
evaluation results, let's shift gears and look at how we can evaluate the
generation component of our RAG pipeline. Assessing the quality of the final
answers produced by the system is equally crucial to gauging the effectiveness
of our retrieval.

Retrieval is only half the story. The true test of our system is the quality
of the final answers it generates by combining retrieved content with LLM
intelligence. In the next section, we'll dive into a parallel evaluation process
for the generation component, exploring both automated metrics and human
assessment to get a well-rounded picture of our RAG pipeline's end-to-end
performance. By shining a light on both halves of the RAG architecture, we'll be
well-equipped to iterate and optimize our way to an ever more capable and
reliable question-answering system.

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/)
repository and for this section, particularly [the `eval_retrieval.py`
file](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/steps/eval_retrieval.py).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
