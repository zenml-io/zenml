---
description: Learn how to implement a RAG pipeline in just 85 lines of code.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


There's a lot of theory and context to think about when it comes to RAG, but
let's start with a quick implementation in code to motivate what follows. The
following 85 lines do the following:

- load some data (a fictional dataset about 'ZenML World') as our corpus
- process that text (split it into chunks and 'tokenize' it (i.e. split into
  words))
- take a query as input and find the most relevant chunks of text from our
  corpus data
- use OpenAI's GPT-3.5 model to answer the question based on the relevant
    chunks

```python
import os
import re
import string

from openai import OpenAI


def preprocess_text(text):
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text):
    return preprocess_text(text).split()


def retrieve_relevant_chunks(query, corpus, top_n=2):
    query_tokens = set(tokenize(query))
    similarities = []
    for chunk in corpus:
        chunk_tokens = set(tokenize(chunk))
        similarity = len(query_tokens.intersection(chunk_tokens)) / len(
            query_tokens.union(chunk_tokens)
        )
        similarities.append((chunk, similarity))
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in similarities[:top_n]]


def answer_question(query, corpus, top_n=2):
    relevant_chunks = retrieve_relevant_chunks(query, corpus, top_n)
    if not relevant_chunks:
        return "I don't have enough information to answer the question."

    context = "\n".join(relevant_chunks)
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"Based on the provided context, answer the following question: {query}\n\nContext:\n{context}",
            },
            {
                "role": "user",
                "content": query,
            },
        ],
        model="gpt-3.5-turbo",
    )

    return chat_completion.choices[0].message.content.strip()


# Sci-fi themed corpus about "ZenML World"
corpus = [
    "The luminescent forests of ZenML World are inhabited by glowing Zenbots that emit a soft, pulsating light as they roam the enchanted landscape.",
    "In the neon skies of ZenML World, Cosmic Butterflies flutter gracefully, their iridescent wings leaving trails of stardust in their wake.",
    "Telepathic Treants, ancient sentient trees, communicate through the quantum neural network that spans the entire surface of ZenML World, sharing wisdom and knowledge.",
    "Deep within the melodic caverns of ZenML World, Fractal Fungi emit pulsating tones that resonate through the crystalline structures, creating a symphony of otherworldly sounds.",
    "Near the ethereal waterfalls of ZenML World, Holographic Hummingbirds hover effortlessly, their translucent wings refracting the prismatic light into mesmerizing patterns.",
    "Gravitational Geckos, masters of anti-gravity, traverse the inverted cliffs of ZenML World, defying the laws of physics with their extraordinary abilities.",
    "Plasma Phoenixes, majestic creatures of pure energy, soar above the chromatic canyons of ZenML World, their fiery trails painting the sky in a dazzling display of colors.",
    "Along the prismatic shores of ZenML World, Crystalline Crabs scuttle and burrow, their transparent exoskeletons refracting the light into a kaleidoscope of hues.",
]

corpus = [preprocess_text(sentence) for sentence in corpus]

question1 = "What are Plasma Phoenixes?"
answer1 = answer_question(question1, corpus)
print(f"Question: {question1}")
print(f"Answer: {answer1}")

question2 = (
    "What kinds of creatures live on the prismatic shores of ZenML World?"
)
answer2 = answer_question(question2, corpus)
print(f"Question: {question2}")
print(f"Answer: {answer2}")

irrelevant_question_3 = "What is the capital of Panglossia?"
answer3 = answer_question(irrelevant_question_3, corpus)
print(f"Question: {irrelevant_question_3}")
print(f"Answer: {answer3}")
```

This outputs the following:

```shell
Question: What are Plasma Phoenixes?
Answer: Plasma Phoenixes are majestic creatures made of pure energy that soar above the chromatic canyons of Zenml World. They leave fiery trails behind them, painting the sky with dazzling displays of colors.
Question: What kinds of creatures live on the prismatic shores of ZenML World?
Answer: On the prismatic shores of ZenML World, you can find crystalline crabs scuttling and burrowing with their transparent exoskeletons, which refract light into a kaleidoscope of hues.
Question: What is the capital of Panglossia?
Answer: The capital of Panglossia is not mentioned in the provided context.
```

The implementation above is by no means sophisticated or performant, but it's
simple enough that you can see all the moving parts. Our tokenization process
consists of splitting the text into individual words. 

The way we check for similarity between the question / query and the chunks of
text is extremely naive and inefficient. The similarity between the query and
the current chunk is calculated using the [Jaccard similarity
coefficient](https://www.statology.org/jaccard-similarity/). This coefficient
measures the similarity between two sets and is defined as the size of the
intersection divided by the size of the union of the two sets. So we count the
number of words that are common between the query and the chunk and divide it by
the total number of unique words in both the query and the chunk. There are much
better ways of measuring the similarity between two pieces of text, such as
using embeddings or other more sophisticated techniques, but this example is
kept simple for illustrative purposes.

The rest of this guide will showcase a more performant and scalable way of
performing the same task using ZenML. If you ever are unsure why we're doing
something, feel free to return to this example for the high-level overview.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
