# Implementation of NLP algorithm using Zenml

This example demonstrates how we can use zenml and huggingface transformers to build, train, & test NLP models. Token-classification is an NLP/NLU task, where we assign labels to tokens in a text, i.e. Name entity recognition, Part of speech tagging etc. In this example, we will train a NER model using the conll2003 dataset.

## Token-classification Modeling Steps

- Load dataset: Load token-classification dataset in this case it is conll2003 dataset
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
cd zenml/examples/nlp/token-classification

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python run_pipeline.py
```

### Test pipeline

```python
from zenml.repository import Repository
from transformers import pipeline
repo = Repository()
p = repo.get_pipeline(pipeline_name="train_eval_pipeline")
runs = p.runs
print(f"Pipeline `load_and_normalize_pipeline` has {len(runs)} run(s)")
latest_run = runs[-1]
trainer_step = latest_run.get_step('trainer')
load_tokenizer_step = latest_run.get_step("load_tokenizer")

# load model and pipeline
model = trainer_step.output.read()
tokenizer = load_tokenizer_step.output.read()
ner = pipeline("token-classification", model=model, tokenizer=tokenizer)

print(ner("Zenml-io is based out of Munich, Germany"))
```