# Evaluation for LLM Finetuning

Evaluations (evals) for Large Language Model (LLM) finetuning are akin to unit tests in traditional software development. They play a crucial role in assessing the performance, reliability, and safety of finetuned models. Like unit tests, evals help ensure that your model behaves as expected and allow you to catch issues early in the development process.

It's easy to feel a sense of paralysis when it comes to evaluations, especially since there are so many things that can potentially fall under the rubric of 'evaluation'. As an alternative, consider keeping the mantra of starting small and slowly building up your evaluation set. This incremental approach will serve you well and allow you to get started out of the gate instead of waiting until your project is too far advanced.

Why do we even need evaluations, and why do we need them (however incremental and small) from the early stages? We want to ensure that our model is performing as intended, catch potential issues early, and track progress over time. Evaluations provide a quantitative and qualitative measure of our model's capabilities, helping us identify areas for improvement and guiding our iterative development process. By implementing evaluations early, we can establish a baseline for performance and make data-driven decisions throughout the finetuning process, ultimately leading to a more robust and reliable LLM.

## Motivation and Benefits

The motivation for implementing thorough evals is similar to that of unit tests in traditional software development:

1. Prevent Regressions: Ensure that new iterations or changes don't negatively impact existing functionality.

2. Track Improvements: Quantify and visualise how your model improves with each iteration or finetuning session.

3. Ensure Safety and Robustness: Given the complex nature of LLMs, comprehensive evals help identify and mitigate potential risks, biases, or unexpected behaviours.

By implementing a robust evaluation strategy, you can develop more reliable, performant, and safe finetuned LLMs while maintaining a clear picture of your model's capabilities and limitations throughout the development process.

## Types of Evaluations

### Custom Evals

Custom evals are tailored to your specific use case and can be categorised into two main types:

1. Success Modes: These evals focus on things you want to see in your model's output, such as:
	- Correct formatting
	- Appropriate responses to specific prompts
	- Desired behaviour in edge cases

2. Failure Modes: These evals target things you don't want to see, including:
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
    "how late is the shopping centre open until?": ["10pm", "22:00", "ten"]
}

for question, answers in good_responses.items():
    llm_response = query_llm(question)
    assert any(answer in llm_response for answer in answers), f"Response does not contain any of the expected answers: {answers}"

bad_responses = {
    "who is the manager of the shopping centre?": ["tom hanks", "spiderman"]
}

for question, answers in bad_responses.items():
    llm_response = query_llm(question)
    assert not any(answer in llm_response for answer in answers), f"Response contains an unexpected answer: {llm_response}"
```

You can see how you might want to expand this out to cover more examples and more failure modes, but this is a good start. As you continue in the work of iterating on your model and performing more tests, you can update these cases with known failure modes (and/or with obvious success modes that your use case must always work for).

### Generalised Evals and Frameworks

Generalised evals and frameworks provide a structured approach to evaluating your finetuned LLM. They offer:

- Assistance in organising and structuring your evals
- Standardised evaluation metrics for common tasks
- Insights into the model's overall performance

When using generalised evals, it's important to consider their limitations and caveats. While they provide valuable insights, they should be complemented with custom evals tailored to your specific use case. Some possible options for you to check out include:

- [prodigy-evaluate](https://github.com/explosion/prodigy-evaluate?tab=readme-ov-file)
- [ragas](https://docs.ragas.io/en/stable/getstarted/monitoring.html)
- [giskard](https://docs.giskard.ai/en/stable/getting_started/quickstart/quickstart_llm.html)
- [langcheck](https://github.com/citadel-ai/langcheck)
- [nervaluate](https://github.com/MantisAI/nervaluate) (for NER)

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
effective way to visualise and monitor progress. These metrics should align with
your iteration goals and capture improvements over time, allowing you to quickly
assess the impact of changes and identify areas that require attention. Again,
as with everything else, don't let perfect be the enemy of the good; a simple
dashboard using  simple technology with a few key metrics is better than no
dashboard at all.
