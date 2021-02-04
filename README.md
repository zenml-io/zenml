<div align="center">

<img src="https://zenml.io/assets/social/github.svg">


<p align="center">
  <a href="https://zenml.io">ZenML.io</a> •
  <a href="https://docs.zenml.io">docs.ZenML.io</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="https://github.com/maiot-io/zenml/discussions">GitHub Community</a> •
  <a href="https://zenml.io/slack-invite/">Join Slack</a>
</p>

[![PyPI - ZenML Version](https://img.shields.io/pypi/v/zenml.svg?label=pip&logo=PyPI&logoColor=white)](https://pypi.org/project/zenml/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenml)](https://pypi.org/project/zenml/)
[![PyPI Status](https://pepy.tech/badge/zenml)](https://pepy.tech/project/zenml)
![GitHub](https://img.shields.io/github/license/maiot-io/zenml)
</div>

<div align="center"> Join our
<a href="https://zenml.io/slack-invite" target="_blank">
    <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
<b>Slack Community</b> </a> join the ZenML family
</div>
<div align="center"> Give us a 
    <img width="25" src="https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png" alt="Slack"/>
<b>GitHub star</b> to show your love!
</div>

## Why?
ZenML is built for ML practitioners who are ramping up their ML workflows towards production. We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML enviornment. Here is what's hard to replicate in production:

* It's hard to **version** data, code, configuration, and models.
* It's difficult to **reproduce** experiments across environments.
* There is no **gold-standard** to organize ML code and manage technical debt as complexity grows.
* It's a struggle to **estabilish a reliable link** between trainings and deployments.
* It's arduous to **track** metadata and artifacts that are produced.

ZenML is not here replace the great tools that solve the individual problems above. Rather, it uses them as [integrations](https://docs.zenml.io/benefits/integrations.html) to expose a coherent, simple path to getting any ML model in production. 

## What is ZenML?
**ZenML** is an extensible, open-source MLOps framework for creating production-ready Machine Learning pipelines - in a simple way. The key features of ZenML are:

* Guaranteed reproducibility of your training experiments. Your pipelines are versioned from data to model, experiments automatically tracked and all pipeline configs are declarative by default.
* Guaranteed comparability between experiments.
* Ability to quickly switch between local and cloud environments (e.g. Kubernetes, Apache Beam).
* Built-in and extensible abstractions for all MLOps needs - from distributed processing on large datasets to Cloud-integrations and model serving backends.
* Pre-built helpers to compare and visualize input parameters as well as pipeline results (e.g. Tensorboard, TFMA, TFDV).
* Cached pipeline states for faster experiment iterations.


## Quickstart 
The quickest way to get started is to The dataset used is the [Pima Indians Diabetes Dataset](https://storage.googleapis.com/zenml_quickstart/diabetes.csv) (originally from the National Institute of Diabetes and Digestive and Kidney Diseases) 


#### Step 0: Installation

ZenML is available for easy installation into your environment via PyPI:
```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge:
**NOTE:** Do so on your own risk, no guarantees given!
```bash
pip install git+https://github.com/maiot-io/zenml.git@main --upgrade
```

#### Step 1: Initialize a ZenML repo from within a git repo

```bash
zenml init
```

#### Step 2: Assemble, run and evaluate your pipeline locally

```python
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.preprocesser.standard_preprocesser.standard_preprocesser import StandardPreprocesser
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import FeedForwardTrainer

training_pipeline = TrainingPipeline(name='Quickstart')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes Dataset', 
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a random 70/30 train-eval split
training_pipeline.add_split(RandomSplit(split_map={'train': 0.7, 'eval': 0.3}))

# StandardPreprocesser() has sane defaults for normal preprocessing methods
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer
training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Run the pipeline locally
training_pipeline.run()
```

To make this work for your existing codebase, follow our guide to convert you legacy codebase into ZenML code [here](https://docs.zenml.io/getting-started/organizing-zenml.html).

## Leverage powerful integrations
Once code is organized into a ZenML pipeline, you can supercharge your ML development through powerful [integrations](https://docs.zenml.io/benefits/integrations.html). Some of the benefits you get are:

### Work locally but switch seamlessly to the cloud

### Versioning galore
Code is versioned 
Data is versioned
Models are versioned
Configurations are versioned

### Automatically detect schema
```python
# See schema of data
training_pipeline.view_schema()
```

### View statistics
```python
# See statistics of train and eval
training_pipeline.view_statistics()
```
![ZenML statistics visualization](docs/zenml_statistics.gif)

### Evaluate the model using built-in evaluators
```python
# Creates a notebook for evaluation
training_pipeline.evaluate()
```

### Compare training pipelines
```python
repo.compare_training_pipelines()
```

### Deploy models automatically

### Distribute preprocessing to the cloud
Of course, each of these steps can be [extended quite easily](https://docs.zenml.io/steps/creating-custom-steps) to accommodate more complex scenarios and use-cases. There is a steadily-growing number of integrations available, 
for example Google Dataflow for [distributed preprocessing](https://docs.zenml.io/backends/processing-backends) or Google Cloud AI Platform as a 
[training](https://docs.zenml.io/backends/training-backends) backend. 

You can also run these pipelines on a cloud VM, for example on a Google Cloud Platform VM, [with a few more lines of code](https://docs.zenml.io/tutorials/running-a-pipeline-on-a-google-cloud-vm).

### Train on spot instances
Train on spot instances

The best part is that ZenML is extensible easily, and can be molded to your use-case. You can create your own custom logic or create a PR 
and contribute to the ZenML community, so that everyone can benefit.

## Community
Our community is the backbone of making ZenML a success! We are currently actively maintaining two main channels for community discussions:

* Our Slack Channel: Chat with us [here](https://zenml.io/slack-invite/).
* The GitHub Community: Create your first thread [here](https://github.com/maiot-io/zenml/discussions).

## Contributing
We would love to receive your contributions! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how to contribute best.

## Copyright
ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository.

Any contribution made to this project will be licensed under the Apache License Version 2.0.

## Credit
ZenML is built on the shoulders of giants: We leverage, and would like to give credit to, existing open-source libraries like [TFX](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher level interface with the focus being purely on easy-of-use and coherent intuitive design.
You can read more about why we actually started building ZenML at our [blog](https://blog.maiot.io/why-zenml/).
