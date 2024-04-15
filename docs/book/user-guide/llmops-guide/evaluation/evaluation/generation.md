---
description: Evaluate the generation component of your RAG pipeline.
---

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
exclude terms like "Flyte" or "Prefect". These handcrafted tests should be
driven by mistakes that you've already seen in the RAG output. The negative
example of "Flyte" and "Prefect" showing up in the list of supported
orchestrators, for example, shows up sometimes when you use GPT 3.5 as the LLM.

As another example, when you make a query asking 'what is the default
orchestrator in ZenML?' you would expect that the answer would include the word
'local', so we can make a test case to confirm that.

You can view our starter set of these tests
[here](https://github.com/zenml-io/zenml-projects/blob/feature/evaluation-llm-complete-guide/llm-complete-guide/steps/eval_e2e.py#L28-L55).
It's better to start with something small and simple and then expand as is
needed. There's no need for complicated harnesses or frameworks at this stage.

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
quantitative approach and can give you a sense of how well your LLM is doing.




<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
