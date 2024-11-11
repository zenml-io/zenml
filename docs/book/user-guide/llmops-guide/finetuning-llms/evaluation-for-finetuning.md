# Evaluation for LLM Finetuning

Evaluations (evals) for Large Language Model (LLM) finetuning are akin to unit tests in traditional software development. They play a crucial role in assessing the performance, reliability, and safety of finetuned models. Like unit tests, evals help ensure that your model behaves as expected and allow you to catch issues early in the development process.

It's easy to feel a sense of paralysis when it comes to evaluations, especially since there are so many things that can potentially fall under the rubric of 'evaluation'. As an alternative, consider keeping the mantra of starting small and slowly building up your evaluation set. This incremental approach will serve you well and allow you to get started out of the gate instead of waiting until your project is too far advanced.

Why do we even need evaluations, and why do we need them (however incremental and small) from the early stages? We want to ensure that our model is performing as intended, catch potential issues early, and track progress over time. Evaluations provide a quantitative and qualitative measure of our model's capabilities, helping us identify areas for improvement and guiding our iterative development process. By implementing evaluations early, we can establish a baseline for performance and make data-driven decisions throughout the finetuning process, ultimately leading to a more robust and reliable LLM.

## Motivation and Benefits

The motivation for implementing thorough evals is similar to that of unit tests in traditional software development:

1. **Prevent Regressions**: Ensure that new iterations or changes don't negatively impact existing functionality.

2. **Track Improvements**: Quantify and visualize how your model improves with each iteration or finetuning session.

3. **Ensure Safety and Robustness**: Given the complex nature of LLMs, comprehensive evals help identify and mitigate potential risks, biases, or unexpected behaviors.

By implementing a robust evaluation strategy, you can develop more reliable, performant, and safe finetuned LLMs while maintaining a clear picture of your model's capabilities and limitations throughout the development process.

## Types of Evaluations

It's common for finetuning projects to use generic out-of-the-box evaluation
frameworks, but it's also useful to understand how to implement custom evals
for your specific use case. In the end, building out a robust set of evaluations
is a crucial part of knowing whether what you finetune is actually working. It
also will allow you to benchmark your progress over time as well as check --
when a new model gets released -- whether it even makes sense to continue with
the finetuning work you've done. New open-source and open-weights models are
released all the time, and you might find that your use case is better solved by
a new model. Evaluations will allow you to make this decision.

### Custom Evals

The approach taken for custom evaluations is similar to that used and [showcased
in the RAG guide](../evaluation/README.md), but it is adapted here for the
finetuning use case. The main distinction here is that we are not looking to
evaluate retrieval, but rather the performance of the finetuned model (i.e.
[the generation part](../evaluation/generation.md)).

Custom evals are tailored to your specific use case and can be categorized into two main types:

1. **Success Modes**: These evals focus on things you want to see in your model's output, such as:
	- Correct formatting
	- Appropriate responses to specific prompts
	- Desired behavior in edge cases

2. **Failure Modes**: These evals target things you don't want to see, including:
	- Hallucinations (generating false or nonsensical information)
	- Incorrect output formats
	- Biased or insulting responses
	- Garbled or incoherent text
	- Failure to handle edge cases appropriately

In terms of what this might look like in code, you can start off really simple and grow as your needs and understanding expand. For example, you could test some success and failure modes simply in the following way:

```python
from my_library import query_llm

good_responses = {
    "what are the best salads available at the food court?": ["caesar", "italian"],
    "how late is the shopping center open until?": ["10pm", "22:00", "ten"]
}

for question, answers in good_responses.items():
    llm_response = query_llm(question)
    assert any(answer in llm_response for answer in answers), f"Response does not contain any of the expected answers: {answers}"

bad_responses = {
    "who is the manager of the shopping center?": ["tom hanks", "spiderman"]
}

for question, answers in bad_responses.items():
    llm_response = query_llm(question)
    assert not any(answer in llm_response for answer in answers), f"Response contains an unexpected answer: {llm_response}"
```

You can see how you might want to expand this out to cover more examples and more failure modes, but this is a good start. As you continue in the work of iterating on your model and performing more tests, you can update these cases with known failure modes (and/or with obvious success modes that your use case must always work for).

### Generalized Evals and Frameworks

Generalized evals and frameworks provide a structured approach to evaluating your finetuned LLM. They offer:

- Assistance in organizing and structuring your evals
- Standardized evaluation metrics for common tasks
- Insights into the model's overall performance

When using Generalized evals, it's important to consider their limitations and caveats. While they provide valuable insights, they should be complemented with custom evals tailored to your specific use case. Some possible options for you to check out include:

- [prodigy-evaluate](https://github.com/explosion/prodigy-evaluate?tab=readme-ov-file)
- [ragas](https://docs.ragas.io/en/stable/getstarted/monitoring.html)
- [giskard](https://docs.giskard.ai/en/stable/getting_started/quickstart/quickstart_llm.html)
- [langcheck](https://github.com/citadel-ai/langcheck)
- [nervaluate](https://github.com/MantisAI/nervaluate) (for NER)

It's easy to build in one of these frameworks into your ZenML pipeline. The
implementation of evaluation in [the `llm-lora-finetuning` project](https://github.com/zenml-io/zenml-projects/tree/main/llm-lora-finetuning) is a good
example of how to do this. We used the `evaluate` library for ROUGE evaluation,
but you could easily swap this out for another framework if you prefer. See [the previous section](finetuning-with-accelerate.md#implementation-details) for more details.

## Data and Tracking

Regularly examining the data your model processes during inference is crucial for identifying patterns, issues, or areas for improvement. This analysis of inference data provides valuable insights into your model's real-world performance and helps guide future iterations. Whatever you do, just keep it simple at the beginning. Keep the 'remember to look at your data' mantra in your mind and set up some sort of repeated pattern or system that forces you to keep looking at the inference calls being made on your finetuned model. This will allow you to pick up the patterns of things that are working and failing for your model.

As part of this, implementing comprehensive logging from the early stages of development is essential for tracking your model's progress and behavior. Consider using frameworks specifically designed for LLM evaluation to streamline this process, as they can provide structured approaches to data collection and analysis. Some recommended possible options include:

- [weave](https://github.com/wandb/weave)
- [openllmetry](https://github.com/traceloop/openllmetry)
- [langsmith](https://smith.langchain.com/)
- [langfuse](https://langfuse.com/)
- [braintrust](https://www.braintrust.dev/)

Alongside collecting the raw data and viewing it periodically, creating simple
dashboards that display core metrics reflecting your model's performance is an
effective way to visualize and monitor progress. These metrics should align with
your iteration goals and capture improvements over time, allowing you to quickly
assess the impact of changes and identify areas that require attention. Again,
as with everything else, don't let perfect be the enemy of the good; a simple
dashboard using  simple technology with a few key metrics is better than no
dashboard at all.
