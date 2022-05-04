# [⚗️ SciPy](https://scipy.org/) sparse matrices in ZenML

An elementary data structure widely used in `sklearn` to store sparse data more
efficiently.

## 🧰 How the example is implemented

We train a simple linear model to classify sentences based on emotion using
the [Emotions dataset for NLP](https://www.kaggle.com/datasets/praveengovi/emotions-dataset-for-nlp)
. The text is represented as a
sparse [n-gram](https://en.wikipedia.org/wiki/N-gram) feature vector.

Example input : `[["I love dogs"], ["I love cats"]]`

If we set `n = 2`, the n-gram vectorizer will find
the [bigrams](https://en.wikipedia.org/wiki/Bigram) `"I love"`, `"love dogs"`,
and `"love cats"`

Output features : `[[1, 1, 0], [1, 0, 1]]`

# 🖥 Run it locally

## ⏩ SuperQuick `scipy` run

If you're really in a hurry and just want to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run scipy
```

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install scipy

# pull example
zenml example pull scipy
cd zenml_examples/scipy

# Initialize ZenML repo
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
