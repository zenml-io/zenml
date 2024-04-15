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




<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
