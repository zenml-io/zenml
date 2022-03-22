# Implementation of NLP algorithms using Zenml

NLP is a branch of machine learning that is about helping systems to understand natural text and spoken words in the same way that humans do.

The following is a list of common NLP tasks:

- Classification of sentences: sequence-classification
- Classification of each words in a sentence: token-classification
- Extraction of answer from a context text: question-answering
- Text generation using prompt: text-generation
- Translation: text-translation

These examples demonstrate how we can use zenml and huggingface transformers to build, train, & test NLP models.

## Sequence Classification

Sequence Classification is an NLP/NLU task, where we assign labels to a given text, i.e. sentiment classification, natural langauge inference etc. In this example, we will train a sentiment classification model using the [`imdb`](https://www.kaggle.com/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews) dataset.

- Load dataset: Load sequence-classification dataset in this case it is `imdb` dataset
- Load pre-trained tokenizer: Load pre-trained tokenizer from huggingface transformers.
- Tokenize and Prepare dataset for training: Use pre-trained tokenizer to tokenize and encode dataset into ids along with labels
- Build and Train Model: You can build model or use pre-trained models from huggingface transformers. Use encoded dataset to train model.
- Evaluate: Evaluate model loss and accuracy


## Token Classification

Token Classification is an NLP/NLU task, where we assign labels to tokens in a text, i.e. Name entity recognition, Part of speech tagging etc. In this example, we will train a NER model using the `conll2003` dataset.

- Load dataset: Load token-classification dataset in this case it is `conll2003` dataset
- Load pre-trained tokenizer: Load pre-trained tokenizer from huggingface transformers.
- Tokenize and Prepare dataset for training: Use pre-trained tokenizer to tokenize and encode dataset into ids along with labels
- Build and Train Model: You can build model or use pre-trained models from huggingface transformers. Use encoded dataset to train model.
- Evaluate: Evaluate model loss and accuracy

## Run it locally

```shell
# install CLI
pip install zenml transformers datasets

# install ZenML integrations
zenml integration install mlflow
zenml integration install tensorflow

# pull example
cd zenml/examples/huggingface

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
# sequence-classification
python run_pipeline.py --nlp_task=sequence-classification --pretrained_model=distilbert-base-uncased --epochs=3 --batch_size=16

# token-classification
python run_pipeline.py --nlp_task=token-classification --pretrained_model=distilbert-base-uncased --epochs=3 --batch_size=16
```

### Test pipeline

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