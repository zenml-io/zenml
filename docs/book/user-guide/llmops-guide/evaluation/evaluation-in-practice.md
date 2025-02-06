---
description: Learn how to evaluate the performance of your RAG system in practice.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Evaluation in practice

Now that we've seen individually how to evaluate the retrieval and generation components of our pipeline, it's worth taking a step back to think through how all of this works in practice.

Our example project includes the evaluation as a separate pipeline that optionally runs after the main pipeline that generates and populates the embeddings. This is a good practice to follow, as it allows you to separate the concerns of generating the embeddings and evaluating them. Depending on the specific use case, the evaluations could be included as part of the main pipeline and used as a gating mechanism to determine whether the embeddings are good enough to be used in production.

Given some of the performance constraints of the LLM judge, it might be worth experimenting with using a local LLM judge for evaluation during the course of the development process and then running the full evaluation using a cloud LLM like Anthropic's Claude or OpenAI's GPT-3.5 or 4. This can help you iterate faster and get a sense of how well your embeddings are performing before committing to the cost of running the full evaluation.

## Automated evaluation isn't a silver bullet

While automating the evaluation process can save you time and effort, it's important to remember that it doesn't replace the need for a human to review the results. The LLM judge is expensive to run, and it takes time to get the results back. Automating the evaluation process can help you focus on the details and the data, but it doesn't replace the need for a human to review the results and make sure that the embeddings (and the RAG system as a whole) are performing as expected.

## When and how much to evaluate

The frequency and depth of evaluation will depend on your specific use case and the constraints of your project. In an ideal world, you would evaluate the performance of your embeddings and the RAG system as a whole as often as possible, but in practice, you'll need to balance the cost of running the evaluation with the need to iterate quickly.

Some tests can be run quickly and cheaply (notably the tests of the retrieval system) while others (like the LLM judge) are more expensive and time-consuming. You should structure your RAG tests and evaluation to reflect this, with some tests running frequently and others running less often, just as you would in any other software project.

There's more we could improve our evaluation system, but for now we can continue onwards to [adding a reranker](../reranking/README.md) to improve our retrieval. This will allow us to improve the performance of our retrieval system without needing to retrain the embeddings. We'll cover this in the next section.

## Try it out!

To see how this works in practice, you can run the evaluation pipeline using the project code. This will give you a sense of how the evaluation process works in practice and you can of course then play with and modify the evaluation code.

To run the evaluation pipeline, first clone the project repository:

```bash
git clone https://github.com/zenml-io/zenml-projects.git
```

Then navigate to the `llm-complete-guide` directory and follow the instructions in the `README.md` file to run the evaluation pipeline. (You'll have to have first run the main pipeline to generate the embeddings.)

To run the evaluation pipeline, you can use the following command:

```bash
python run.py --evaluation
```

This will run the evaluation pipeline and output the results to the console. You can then inspect the progress, logs and results in the dashboard!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
