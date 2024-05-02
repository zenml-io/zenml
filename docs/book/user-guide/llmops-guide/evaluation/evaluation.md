---
description: Track how your RAG pipeline improves using evaluation and metrics.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Evaluation and metrics for LLMOps

In this section, we'll explore how to evaluate the performance of your RAG
pipeline using metrics and visualizations. Evaluating your RAG pipeline is
crucial to understanding how well it performs and identifying areas for
improvement. With language models in particular, it's hard to evaluate their
performance using traditional metrics like accuracy, precision, and recall. This
is because language models generate text, which is inherently subjective and
difficult to evaluate quantitatively.

Our RAG pipeline is a whole system, moreover, not just a model, and evaluating
it requires a holistic approach. We'll look at various ways to evaluate the
performance of your RAG pipeline but the two main areas we'll focus on are:

- [Retrieval evaluation](retrieval.md), so checking that the
  retrieved documents or document chunks are relevant to the query.
- [Generation evaluation](generation.md), so checking that the
  generated text is coherent and helpful for our specific use case.

![](/docs/book/.gitbook/assets/evaluation-two-parts.png)

In the previous section we built out a basic RAG pipeline for our documentation
question-and-answer use case. We'll use this pipeline to demonstrate how to
evaluate the performance of your RAG pipeline.

{% hint style="info" %}
If you were running this in a production setting, you might want to set up evaluation
to check the performance of a raw LLM model (i.e. without any retrieval / RAG
components) as a baseline, and then compare this to the performance of your RAG
pipeline. This will help you understand how much value the retrieval and
generation components are adding to your system. We won't cover this here, but
it's a good practice to keep in mind.
{% endhint %}

## What are we evaluating?

When evaluating the performance of your RAG pipeline, your specific use case and
the extent to which you can tolerate errors or lower performance will determine
what you need to evaluate. For instance, if you're building a user-facing
chatbot, you might need to evaluate the following:

- Are the retrieved documents relevant to the query?
- Is the generated answer coherent and helpful for your specific use case?
- Does the generated answer contain hate speech or any sort of toxic language?

These are just examples, and the specific metrics and methods you use will
depend on your use case. The [generation evaluation](generation.md) functions as
an end-to-end evaluation of the RAG pipeline, as it checks the final output of
the system. It's during these end-to-end evaluations that you'll have most
leeway to use subjective metrics, as you're evaluating the system as a whole.

Before we dive into the details, let's take a moment to look at [a short high-level code example](evaluation-in-65-loc.md) showcasing the two main areas of evaluation. Afterwards
the following sections will cover the two main areas of evaluation in more
detail [as well as offer practical
guidance](evaluation/evaluation-in-practice.md) on when to run these evaluations
and what to look for in the results.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
