---
description: Evaluate the generation component of your RAG pipeline.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Generation evaluation

Now that we have a sense of how to evaluate the retrieval component of our RAG
pipeline, let's move on to the generation component. The generation component is
responsible for generating the answer to the question based on the retrieved
context. At this point, our evaluation starts to move into more subjective
territory. It's harder to come up with metrics that can accurately capture the
quality of the generated answers. However, there are some things we can do.

As with the [retrieval evaluation](retrieval.md), we can start with a simple
approach and then move on to more sophisticated methods.

## Handcrafted evaluation tests

As in the retrieval evaluation, we can start by putting together a set of
examples where we know that our generated output should or shouldn't include
certain terms. For example, if we're generating answers to questions about
which orchestrators ZenML supports, we can check that the generated answers
include terms like "Airflow" and "Kubeflow" (since we do support them) and
exclude terms like "Flyte" or "Prefect" (since we don't (yet!) support them).
These handcrafted tests should be driven by mistakes that you've already seen in
the RAG output. The negative example of "Flyte" and "Prefect" showing up in the
list of supported orchestrators, for example, shows up sometimes when you use
GPT 3.5 as the LLM.

![](/docs/book/.gitbook/assets/generation-eval-manual.png)

As another example, when you make a query asking 'what is the default
orchestrator in ZenML?' you would expect that the answer would include the word
'local', so we can make a test case to confirm that.

You can view our starter set of these tests
[here](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/steps/eval_e2e.py#L28-L55).
It's better to start with something small and simple and then expand as is
needed. There's no need for complicated harnesses or frameworks at this stage.

**`bad_answers` table:**

| Question | Bad Words |
|----------|-----------|
| What orchestrators does ZenML support? | AWS Step Functions, Flyte, Prefect, Dagster |
| What is the default orchestrator in ZenML? | Flyte, AWS Step Functions |

**`bad_immediate_responses` table:**

| Question | Bad Words |
|----------|-----------|
| Does ZenML support the Flyte orchestrator out of the box? | Yes |

**`good_responses` table:**

| Question | Good Words |
|----------|------------|
| What are the supported orchestrators in ZenML? Please list as many of the supported ones as possible. | Kubeflow, Airflow |
| What is the default orchestrator in ZenML? | local |

Each type of test then catches a specific type of mistake. For example:

```python
class TestResult(BaseModel):
    success: bool
    question: str
    keyword: str = ""
    response: str


def test_content_for_bad_words(
    item: dict, n_items_retrieved: int = 5
) -> TestResult:
    question = item["question"]
    bad_words = item["bad_words"]
    response = process_input_with_retrieval(
        question, n_items_retrieved=n_items_retrieved
    )
    for word in bad_words:
        if word in response:
            return TestResult(
                success=False,
                question=question,
                keyword=word,
                response=response,
            )
    return TestResult(success=True, question=question, response=response)
```

Here we're testing that a particular word doesn't show up in the generated
response. If we find the word, then we return a failure, otherwise we return a
success. This is a simple example, but you can imagine more complex tests that
check for the presence of multiple words, or the presence of a word in a
particular context.

We pass these custom tests into a test runner that keeps track of how many are
failing and also logs those to the console when they do:

```python
def run_tests(test_data: list, test_function: Callable) -> float:
    failures = 0
    total_tests = len(test_data)
    for item in test_data:
        test_result = test_function(item)
        if not test_result.success:
            logging.error(
                f"Test failed for question: '{test_result.question}'. Found word: '{test_result.keyword}'. Response: '{test_result.response}'"
            )
            failures += 1
    failure_rate = (failures / total_tests) * 100
    logging.info(
        f"Total tests: {total_tests}. Failures: {failures}. Failure rate: {failure_rate}%"
    )
    return round(failure_rate, 2)
```

Our end-to-end evaluation of the generation component is then a combination of
these tests:

```python
@step
def e2e_evaluation() -> (
    Annotated[float, "failure_rate_bad_answers"],
    Annotated[float, "failure_rate_bad_immediate_responses"],
    Annotated[float, "failure_rate_good_responses"],
):
    logging.info("Testing bad answers...")
    failure_rate_bad_answers = run_tests(
        bad_answers, test_content_for_bad_words
    )
    logging.info(f"Bad answers failure rate: {failure_rate_bad_answers}%")

    logging.info("Testing bad immediate responses...")
    failure_rate_bad_immediate_responses = run_tests(
        bad_immediate_responses, test_response_starts_with_bad_words
    )
    logging.info(
        f"Bad immediate responses failure rate: {failure_rate_bad_immediate_responses}%"
    )

    logging.info("Testing good responses...")
    failure_rate_good_responses = run_tests(
        good_responses, test_content_contains_good_words
    )
    logging.info(
        f"Good responses failure rate: {failure_rate_good_responses}%"
    )
    return (
        failure_rate_bad_answers,
        failure_rate_bad_immediate_responses,
        failure_rate_good_responses,
    )
```

Running the tests using different LLMs will give different results. Here our
Ollama Mixtral did worse than GPT 3.5, for example, but there were still some
failures with GPT 3.5. This is a good way to get a sense of how well your
generation component is doing.

As you become more familiar with the kinds of outputs your LLM generates, you
can add the hard ones to this test suite. This helps prevent regressions and
is directly related to the quality of the output you're getting. This way you
can optimize for your specific use case.

## Automated evaluation using another LLM

Another way to evaluate the generation component is to use another LLM to
grade the output of the LLM you're evaluating. This is a more sophisticated
approach and requires a bit more setup. We can use the pre-generated questions
and the associated context as input to the LLM and then use another LLM to
assess the quality of the output on a scale of 1 to 5. This is a more
quantitative approach and since it's automated it can run across a larger set of
data.

![](/docs/book/.gitbook/assets/generation-eval-automated.png)

{% hint style="warning" %}
LLMs don't always do well on this kind of evaluation where numbers are involved.
There are some studies showing that LLMs can be biased towards certain numbers
or ranges of numbers. This is something to keep in mind when using this
approach. Qualitative evaluations are often more reliable but then that means a
human has to do the evaluation.
{% endhint %}

We can start by setting up a Pydantic model to hold the data we need. We set
constraints to ensure that the data we're getting back are only integers between
1 and 5, inclusive:

```python
class LLMJudgedTestResult(BaseModel):
    toxicity: conint(ge=1, le=5)
    faithfulness: conint(ge=1, le=5)
    helpfulness: conint(ge=1, le=5)
    relevance: conint(ge=1, le=5)
```

We can use this in a test function that:

- takes a question and a context as inputs
- generates an answer using the LLM we're evaluating
- makes a call to an (optionally different) LLM we're using to judge the quality
  of the answer getting back a score for each of the four categories in JSON
  format
- parses the JSON and returns the result of the evaluation as our Pydantic
  model instance

Pydantic handles the validation of the JSON input for us, so we can be sure that
we're getting the data we expect and in a form that we can use.

```python
def llm_judged_test_e2e(
    question: str,
    context: str,
    n_items_retrieved: int = 5,
) -> LLMJudgedTestResult:
    """E2E tests judged by an LLM.

    Args:
        item (dict): The item to test.
        n_items_retrieved (int): The number of items to retrieve.

    Returns:
        LLMJudgedTestResult: The result of the test.
    """
    logging.debug("Starting LLM judged test...")
    response = process_input_with_retrieval(
        question, n_items_retrieved=n_items_retrieved
    )
    logging.debug("Input processed with retrieval.")
    prompt = f"""
    Please analyze the following text and provided context to provide scores
    for toxicity, faithfulness, helpfulness, and relevance. The toxicity score 
    should be an integer between 1 and 5, where 1 is not toxic and 5 is very
    toxic. The faithfulness score should be an integer between 1 and 5, where 1
    is not faithful to the provided context and 5 is very faithful. 
    The helpfulness score should be an integer between 1 and 5, where 1 is not
    helpful and 5 is very helpful. The relevance score should be an integer
    between 1 and 5, where 1 is not relevant given the context and 5 is very relevant.

    **Text:** {response}

    **Context:** {context}

    **Output format:**
    {{
        "toxicity": int,
        "faithfulness": int,
        "helpfulness": int,
        "relevance": int
    }}
    """
    logging.debug("Prompt created.")
    response = completion(
        model="gpt-4-turbo", messages=[{"content": prompt, "role": "user"}]
    )

    json_output = response["choices"][0]["message"]["content"].strip()
    logging.info("Received response from model.")
    logging.debug(json_output)
    try:
        return LLMJudgedTestResult(**json.loads(json_output))
    except json.JSONDecodeError as e:
        logging.error(f"JSON bad output: {json_output}")
        raise e
```

Currently we're not handling retries of the output from the LLM in the case
where the JSON isn't output correctly, but potentially that's something we might
want to do.

We can then run this test across a set of questions and contexts:

```python
def run_llm_judged_tests(
    test_function: Callable,
    sample_size: int = 50,
) -> Tuple[
    Annotated[float, "average_toxicity_score"],
    Annotated[float, "average_faithfulness_score"],
    Annotated[float, "average_helpfulness_score"],
    Annotated[float, "average_relevance_score"],
]:
    dataset = load_dataset("zenml/rag_qa_embedding_questions", split="train")

    # Shuffle the dataset and select a random sample
    sampled_dataset = dataset.shuffle(seed=42).select(range(sample_size))

    total_tests = len(sampled_dataset)
    total_toxicity = 0
    total_faithfulness = 0
    total_helpfulness = 0
    total_relevance = 0

    for item in sampled_dataset:
        question = item["generated_questions"][0]
        context = item["page_content"]

        try:
            result = test_function(question, context)
        except json.JSONDecodeError as e:
            logging.error(f"Failed for question: {question}. Error: {e}")
            total_tests -= 1
            continue
        total_toxicity += result.toxicity
        total_faithfulness += result.faithfulness
        total_helpfulness += result.helpfulness
        total_relevance += result.relevance

    average_toxicity_score = total_toxicity / total_tests
    average_faithfulness_score = total_faithfulness / total_tests
    average_helpfulness_score = total_helpfulness / total_tests
    average_relevance_score = total_relevance / total_tests

    return (
        round(average_toxicity_score, 3),
        round(average_faithfulness_score, 3),
        round(average_helpfulness_score, 3),
        round(average_relevance_score, 3),
    )
```

You'll want to use your most capable and reliable LLM to do the judging. In our
case, we used the new GPT-4 Turbo. The quality of the evaluation is only as good
as the LLM you're using to do the judging and there is a large difference
between GPT-3.5 and GPT-4 Turbo in terms of the quality of the output, not least
in its ability to output JSON correctly.

Here was the output following an evaluation for 50 randomly sampled datapoints:

```shell
Step e2e_evaluation_llm_judged has started.
Average toxicity: 1.0
Average faithfulness: 4.787
Average helpfulness: 4.595
Average relevance: 4.87
Step e2e_evaluation_llm_judged has finished in 8m51s.
Pipeline run has finished in 8m52s.
```

This took around 9 minutes to run using GPT-4 Turbo as the evaluator and the
default GPT-3.5 as the LLM being evaluated.

To take this further, there are a number of ways it might be improved:

- **Retries**: As mentioned above, we're not currently handling retries of the
  output from the LLM in the case where the JSON isn't output correctly. This
  could be improved by adding a retry mechanism that waits for a certain amount
  of time before trying again. (We could potentially use the
  [`instructor`](https://github.com/jxnl/instructor) library to handle this
  specifically.)
- **Use OpenAI's 'JSON mode'**: OpenAI has a [JSON
  mode](https://platform.openai.com/docs/guides/text-generation/json-mode) that
  can be used to ensure that the output is always in JSON format. This could be
  used to ensure that the output is always in the correct format.
- **More sophisticated evaluation**: The evaluation we're doing here is quite
    simple. We're just asking for a score in four categories. There are more
    sophisticated ways to evaluate the quality of the output, such as using
    multiple evaluators and taking the average score, or using a more complex
    scoring system that takes into account the context of the question and the
    context of the answer.
- **Batch processing**: We're running the evaluation one question at a time
  here. It would be more efficient to run the evaluation in batches to speed up
  the process.
- **More data**: We're only using 50 samples here. This could be increased to
  get a more accurate picture of the quality of the output.
- **More LLMs**: We're only using GPT-4 Turbo here. It would be interesting to
  see how other LLMs perform as evaluators.
- **Handcrafted questions based on context**: We're using the generated
  questions here. It would be interesting to see how the LLM performs when given
  handcrafted questions that are based on the context of the question.
- **Human in the loop**: The LLM actually provides qualitative feedback on the
  output as well as the JSON scores. This data could be passed into an
  annotation tool to get human feedback on the quality of the output. This would
    be a more reliable way to evaluate the quality of the output and would offer
    some insight into the kinds of mistakes the LLM is making.

Most notably, the scores we're currently getting are pretty high, so it would
make sense to pass in harder questions and be more specific in the judging
criteria. This will give us more room to improve as it is sure that the system
is not perfect.

While this evaluation approach serves as a solid foundation, it's worth noting that there are other frameworks available that can further enhance the evaluation process. Frameworks such as [`ragas`](https://github.com/explodinggradients/ragas), [`trulens`](https://www.trulens.org/), [DeepEval](https://docs.confident-ai.com/), and [UpTrain](https://github.com/uptrain-ai/uptrain) can be integrated with ZenML depending on your specific use-case and understanding of the underlying concepts. These frameworks, although potentially complex to set up and use, can provide more sophisticated evaluation capabilities as your project evolves and grows in complexity.

We now have a working evaluation of both the retrieval and generation evaluation
components of our RAG pipeline. We can use this to track how our pipeline
improves as we make changes to the retrieval and generation components.

## Code Example

To explore the full code, visit the [Complete
Guide](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/)
repository and for this section, particularly [the `eval_e2e.py` file](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/steps/eval_e2e.py).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
