---
description: Track how your RAG pipeline improves using evaluation and metrics.
---

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
performance of your RAG pipeline but the three main areas we'll focus on are:

- [Retrieval evaluation](evaluation/retrieval.md), so checking that the retrieved documents or document chunks are relevant to
  the query.
- [Generation evaluation](evaluation/generation.md), so checking that the generated text is coherent and
  helpful for our specific use case.
- [End-to-end evaluation](evaluation/e2e.md), so checking the performance of the whole pipeline from
    query to answer.

In the previous section we built out a basic RAG pipeline for our documentation
question-and-answer use case. We'll use this pipeline to demonstrate how to
evaluate the performance of your RAG pipeline. If you were running this in a
real setting, you might want to set up evaluation to check the performance of a
raw LLM model (i.e. without any retrieval / RAG components) as a baseline, and
then compare this to the performance of your RAG pipeline. This will help you
understand how much value the retrieval and generation components are adding to
your system. We won't cover this here, but it's a good practice to
keep in mind.

The following sections will cover the three main areas of evaluation in more
detail [as well as offer practical guidance](evaluation/evaluation-in-practice.md) on when to run these evaluations and
what to look for in the results.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
