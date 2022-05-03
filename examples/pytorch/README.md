# 🔦 Using PyTorch with ZenML

This example demonstrate how we can use ZenML and Torch to build, train, & test ML models.

[PyTorch](https://pytorch.org/) is an open source machine learning framework that accelerates the path from research prototyping to production deployment.


# 🖥 Run it locally

### 📄 Prerequisites

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install pytorch -f
pip install -r requirements.txt  # for torchvision

# pull example
cd zenml/examples/pytorch

# initialize
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute one of the below lines to run the code:

```shell
# sequence-classification
python run.py
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