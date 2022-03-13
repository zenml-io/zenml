# Implementation of NLP algorithm using Zenml

This example build to train nlp algorithm using Zenml pipelines.

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
from transformers import AutoTokenizer, pipeline
repo = Repository()
p = repo.get_pipeline(pipeline_name="train_eval_pipeline")
runs = p.runs
print(f"Pipeline `load_and_normalize_pipeline` has {len(runs)} run(s)")
latest_run = runs[-1]
trainer_step = latest_run.get_step('trainer')

# load model and pipeline
model = trainer_step.output.read()
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
ner = pipeline("token-classification", model=model, tokenizer=tokenizer)

print(ner("I love my country India"))
```