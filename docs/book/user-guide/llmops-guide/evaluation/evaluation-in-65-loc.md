---
description: Learn how to implement evaluation for RAG in just 65 lines of code.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Evaluation in 65 lines of code

Our RAG guide included [a short example](../rag-with-zenml/rag-85-loc.md) for how to implement a basic RAG pipeline in just 85 lines of code. In this section, we'll build on that example to show how you can evaluate the performance of your RAG pipeline in just 65 lines. For the full code, please visit the project repository [here](https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/most\_basic\_eval.py). The code that follows requires the functions from the earlier RAG pipeline code to work.

```python
# ...previous RAG pipeline code here...
# see https://github.com/zenml-io/zenml-projects/blob/main/llm-complete-guide/most_basic_rag_pipeline.py

eval_data = [
    {
        "question": "What creatures inhabit the luminescent forests of ZenML World?",
        "expected_answer": "The luminescent forests of ZenML World are inhabited by glowing Zenbots.",
    },
    {
        "question": "What do Fractal Fungi do in the melodic caverns of ZenML World?",
        "expected_answer": "Fractal Fungi emit pulsating tones that resonate through the crystalline structures, creating a symphony of otherworldly sounds in the melodic caverns of ZenML World.",
    },
    {
        "question": "Where do Gravitational Geckos live in ZenML World?",
        "expected_answer": "Gravitational Geckos traverse the inverted cliffs of ZenML World.",
    },
]


def evaluate_retrieval(question, expected_answer, corpus, top_n=2):
    relevant_chunks = retrieve_relevant_chunks(question, corpus, top_n)
    score = any(
        any(word in chunk for word in tokenize(expected_answer))
        for chunk in relevant_chunks
    )
    return score


def evaluate_generation(question, expected_answer, generated_answer):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an evaluation judge. Given a question, an expected answer, and a generated answer, your task is to determine if the generated answer is relevant and accurate. Respond with 'YES' if the generated answer is satisfactory, or 'NO' if it is not.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\nExpected Answer: {expected_answer}\nGenerated Answer: {generated_answer}\nIs the generated answer relevant and accurate?",
            },
        ],
        model="gpt-3.5-turbo",
    )

    judgment = chat_completion.choices[0].message.content.strip().lower()
    return judgment == "yes"


retrieval_scores = []
generation_scores = []

for item in eval_data:
    retrieval_score = evaluate_retrieval(
        item["question"], item["expected_answer"], corpus
    )
    retrieval_scores.append(retrieval_score)

    generated_answer = answer_question(item["question"], corpus)
    generation_score = evaluate_generation(
        item["question"], item["expected_answer"], generated_answer
    )
    generation_scores.append(generation_score)

retrieval_accuracy = sum(retrieval_scores) / len(retrieval_scores)
generation_accuracy = sum(generation_scores) / len(generation_scores)

print(f"Retrieval Accuracy: {retrieval_accuracy:.2f}")
print(f"Generation Accuracy: {generation_accuracy:.2f}")
```

As you can see, we've added two evaluation functions: `evaluate_retrieval` and `evaluate_generation`. The `evaluate_retrieval` function checks if the retrieved chunks contain any words from the expected answer. The `evaluate_generation` function uses OpenAI's chat completion LLM to evaluate the quality of the generated answer.

We then loop through the evaluation data, which contains questions and expected answers, and evaluate the retrieval and generation components of our RAG pipeline. Finally, we calculate the accuracy of both components and print the results:

![](../../../.gitbook/assets/evaluation-65-loc.png)

As you can see, we get 100% accuracy for both retrieval and generation in this example. Not bad! The sections that follow will provide a more detailed and sophisticated implementation of RAG evaluation, but this example shows how you can think about it at a high level!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
