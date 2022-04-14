# 🤗 Implementation of NLP algorithms using Hugging Face & ZenML

These examples demonstrate how we can use ZenML and Hugging Face transformers to build, train, & test NLP models.

Huggingface: one of our favorite emoji to express thankfulness, love, or appreciation. In the world of
AI/ML, [`Hugging Face`](https://huggingface.co/) is a startup in the Natural Language Processing (NLP) domain -- now
they are expanding to computer vision and RL -- offering its library of SOTA models in particular around Transformers.
More than a thousand companies use their library in production including Bing, Apple, Microsoft etc. Do checkout
their [`Transformers Library`](https://github.com/huggingface/transformers)
, [`Datasets Library`](https://github.com/huggingface/datasets) and [`Model Hub`](https://huggingface.co/models).

NLP is a branch of machine learning that is about helping systems to understand natural text and spoken words in the
same way that humans do.

The following is a list of common NLP tasks:

- Classification of sentences: sequence-classification
- Classification of each words in a sentence: token-classification
- Extraction of answer from a context text: question-answering
- Text generation using prompt: text-generation
- Translation: text-translation

## 📝 Sequence Classification

Sequence Classification is an NLP/NLU task, where we assign labels to a given text, i.e. sentiment classification,
natural language inference etc. In this example, we will train a sentiment classification model using
the [`imdb`](https://huggingface.co/datasets/imdb) dataset.

- Load dataset: Load sequence-classification dataset in this case it is the `imdb` dataset

```python
    from datasets import load_dataset

datasets = load_dataset("imdb")
print(datasets['train'][0])

{
    'label': 0,  # Sentiment label i.e. 0->Negative 1->Positive
    'text': 'I rented I AM CURIOUS-YELLOW from my video store because of
    all the controversy that surrounded it when it was first released in
                                                             1967. I also heard that at first it was seized
    by U.S.customs if it
    ever tried to enter this country, therefore being a fan of films
    considered controversial I really had to see this
for myself.....'
}
```

- Load pre-trained tokenizer: Load pre-trained tokenizer from Hugging Face transformers.

```python
    from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
```

- Tokenize and prepare dataset for training: Use pre-trained tokenizer to tokenize and encode dataset into ids along
  with labels.
- Build and Train Model: You can build model or use pre-trained models from Hugging Face transformers. Use encoded
  dataset to train model.
- Evaluate: Evaluate model loss and accuracy.

## 🪙 Token Classification

Token Classification is an NLP/NLU task, where we assign labels to tokens in a text, i.e. Name entity recognition,
Part of speech tagging etc. In this example, we will train a NER model using the
[`conll2003`](https://huggingface.co/datasets/conll2003) dataset.

- Load dataset: Load token-classification dataset in this case it is `conll2003` dataset

```python
    from datasets import load_dataset

datasets = load_dataset("conll2003")
print(datasets['train'][0])

{'chunk_tags': [11, 21, 11, 12, 21, 22, 11, 12, 0],
 'id': '0',
 'ner_tags': [3, 0, 7, 0, 0, 0, 7, 0, 0],  # list of token classification labels
 'pos_tags': [22, 42, 16, 21, 35, 37, 16, 21, 7],
 'tokens': ['EU',
            'rejects',
            'German',
            'call',
            'to',
            'boycott',
            'British',
            'lamb',
            '.']}
```

- Load pre-trained tokenizer: Load pre-trained tokenizer from Hugging Face transformers.

```python
    from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
```

- Tokenize and prepare dataset for training: Use pre-trained tokenizer to tokenize and encode dataset into ids along
  with labels.
- Build and Train Model: You can build model or use pre-trained models from huggingface transformers. Use encoded
  dataset to train model.
- Evaluate: Evaluate model loss and accuracy.

# 🖥 Run it locally

### 📄 Prerequisites

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install tensorflow huggingface -f

# pull example
cd zenml/examples/huggingface

# initialize
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```shell
# sequence-classification
python run_pipeline.py --nlp_task=sequence-classification --pretrained_model=distilbert-base-uncased --epochs=1 --batch_size=16 --dataset_name=imdb --text_column=text --label_column=label

# token-classification
python run_pipeline.py --nlp_task=token-classification --pretrained_model=distilbert-base-uncased --epochs=1 --batch_size=16 --dataset_name=conll2003 --text_column=tokens --label_column=ner_tags
```

### 🧪 Test pipeline

```python

from zenml.repository import Repository
from transformers import pipeline

# 1. Load sequence-classification and inference
repo = Repository()
p = repo.get_pipeline(pipeline_name="seq_classifier_train_eval_pipeline")
runs = p.runs
print(f"Pipeline `seq_classifier_train_eval_pipeline` has {len(runs)} run(s)")
latest_run = runs[-1]
trainer_step = latest_run.get_step('trainer')
load_tokenizer_step = latest_run.get_step("load_tokenizer")

# load model and pipeline
model = trainer_step.output.read()
tokenizer = load_tokenizer_step.output.read()
sentiment_classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

print(sentiment_classifier("MLOps movie by Zenml-io was awesome."))

# 2. Load token-classification and inference
repo = Repository()
p = repo.get_pipeline(pipeline_name="token_classifier_train_eval_pipeline")
runs = p.runs
print(f"Pipeline `token_classifier_train_eval_pipeline` has {len(runs)} run(s)")
latest_run = runs[-1]
trainer_step = latest_run.get_step('trainer')
load_tokenizer_step = latest_run.get_step("load_tokenizer")

# load model and pipeline
model = trainer_step.output.read()
tokenizer = load_tokenizer_step.output.read()
token_classifier = pipeline("token-classification", model=model, tokenizer=tokenizer)

print(token_classifier("Zenml-io is based out of Munich, Germany"))
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
