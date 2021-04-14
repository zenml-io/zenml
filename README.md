<div align="center">

<img src="https://zenml.io/assets/social/github.svg">


<p align="center">
  <a href="https://zenml.io">ZenML.io</a> •
  <a href="https://docs.zenml.io">docs.ZenML.io</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#community">Community</a> •
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
<b>Slack Community</b> </a> and become part of the ZenML family
</div>
<div align="center"> Have questions? Join our weekly
<a href="#community">
    <img width="25" src="https://upload.wikimedia.org/wikipedia/commons/f/f8/01_Icon-Community%402x.png" alt="Slack"/>
<b>community hour</b> </a> and talk to us directly
</div>
<div align="center"> Give us a 
    <img width="25" src="https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png" alt="Slack"/>
<b>GitHub star</b> to show your love
</div>

## Why?
ZenML is built for ML practitioners who are ramping up their ML workflows towards production. We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment. Here is what's hard to replicate in production:

* It's hard to **version** data, code, configuration, and models.
* It's difficult to **reproduce** experiments across environments.
* There is no **gold-standard** to organize ML code and manage technical debt as complexity grows.
* It's a struggle to **establish a reliable link** between training and deployment.
* It's arduous to **track** metadata and artifacts that are produced.

ZenML is not here to replace the great tools that solve the individual problems above. Rather, it uses them as [integrations](https://docs.zenml.io/benefits/integrations.html) to expose a coherent, simple path to getting any ML model in production. 

## What is ZenML?
**ZenML** is an extensible, open-source MLOps framework for creating production-ready Machine Learning pipelines - in a simple way. 

A user of ZenML is asked to break down their ML development into individual [Steps](https://docs.zenml.io/steps/what-is-a-step.html), each representing an individual task in the ML development process. A sequence of  steps put together is a [Pipeline](https://docs.zenml.io/pipelines/what-is-a-pipeline.html). Each pipeline contains a [Datasource](https://docs.zenml.io/datasources/what-is-a-datasource.html), which represents a snapshot of a versioned dataset in time. Lastly, every pipeline (and indeed almost every step) can run in [Backends](https://docs.zenml.io/backends/what-is-a-backend.html), that specify how and where a step is executed.

By developing in pipelines, ML practitioners give themselves a platform to transition from research to production from the very beginning, and are also helped in the research phase by the powerful automations introduced by ZenML.

## Quickstart 
The quickest way to get started is to create a simple pipeline. The dataset used here is the [Pima Indians Diabetes Dataset](https://storage.googleapis.com/zenml_quickstart/diabetes.csv) (originally from the National Institute of Diabetes and Digestive and Kidney Diseases) 

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
from zenml.datasources import CSVDatasource
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.split import RandomSplit
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.trainer import TFFeedForwardTrainer

training_pipeline = TrainingPipeline(name='Quickstart')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes Dataset',
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a random 70/30 train-eval split
training_pipeline.add_split(RandomSplit(split_map={'train': 0.7, 
                                                   'eval': 0.2,
                                                   'test': 0.1}))

# StandardPreprocesser() has sane defaults for normal preprocessing methods
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 
                  'insulin', 'bmi', 'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer
training_pipeline.add_trainer(TFFeedForwardTrainer(
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

While the above is great to get a quick flavor of ZenML, a more practical way to start is to follow our guide to convert your legacy codebase into ZenML code [here](https://docs.zenml.io/getting-started/organizing-zenml.html).

## Leverage powerful integrations
Once code is organized into a ZenML pipeline, you can supercharge your ML development through powerful [integrations](https://docs.zenml.io/benefits/integrations.html). Some of the benefits you get are:

### Work locally but switch seamlessly to the cloud

Switching from local experiments to cloud-based pipelines doesn't need to be complex.

![From local to cloud with one parameter](docs/local-and-clound.png)

### Versioning galore

ZenML makes sure for every pipeline you can trust that:

✅ Code is versioned  
✅ Data is versioned  
✅ Models are versioned  
✅ Configurations are versioned  
![ZenML declarative config](docs/versioning.png)

### Automatically detect schema

```python
# See the schema of your data
training_pipeline.view_schema()
```

![Automatic schema dection](docs/schema.png)


### View statistics
```python
# See statistics of train and eval
training_pipeline.view_statistics()
```
<img src="docs/statistics.png" alt="ZenML statistics visualization" />


### Evaluate the model using built-in evaluators
```python
# Creates a notebook for evaluation
training_pipeline.evaluate()
```

<img src="docs/tensorboard_inline.png" alt="Tensorboard built-in"   />


### Compare training pipelines

```python
repo.compare_training_runs()
```

![ZenML built-in pipeline comparison](docs/compare.png)


### Distribute preprocessing to the cloud
Leverage distributed compute powered by [Apache Beam](https://beam.apache.org/):
```python
training_pipeline.add_preprocesser(
    StandardPreprocesser(...).with_backend(
      ProcessingDataFlowBackend(
        project=GCP_PROJECT,
        num_workers=10,
    ))
)
```
<img src="docs/zenml_distribute.png" alt="ZenML distributed processing"   />

### Train on spot instances
Easily train on spot instances to [save 80% cost](https://towardsdatascience.com/spot-the-difference-in-ml-costs-358202e60266).
```python
training_pipeline.run(
  OrchestratorGCPBackend(
    preemptible=True,  # reduce costs by using preemptible instances
    machine_type='n1-standard-4',
    gpu='nvidia-tesla-k80',
    gpu_count=1,
    ...
  )
  ...
)
```

### Deploy models automatically
Automatically deploy each model with powerful Deployment integrations like [Cortex](examples/cortex).

```python
training_pipeline.add_deployment(
    CortexDeployer(
        api_spec=api_spec,
        predictor=PythonPredictor,
    )
)
```

The best part is that ZenML is extensible easily, and can be molded to your use-case. You can create your own custom logic or create a PR 
and contribute to the ZenML community, so that everyone can benefit.

## Community
Our community is the backbone of making ZenML a success! We are currently actively maintaining two main channels for community discussions:

* Our Slack Channel: Chat with us [here](https://zenml.io/slack-invite/).
* The GitHub Community: Create your first thread [here](https://github.com/maiot-io/zenml/discussions).

From March 23, 2021 onwards, we are hosting a weekly community hour with the entire ZenML fam. Come talk to us about ZenML (or whatever else tickles your fancy)! Community hour 
happens at **Wednesday at 5PM GMT+2**. Register in advance [here](https://calendly.com/zenml/community-hour) to join.

## Contributing
We would love to receive your contributions! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how to contribute best.

## Copyright
ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository.

Any contribution made to this project will be licensed under the Apache License Version 2.0.

## Credit
ZenML is built on the shoulders of giants: We leverage, and would like to give credit to, existing open-source libraries like [TFX](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher level interface with the focus being purely on easy-of-use and coherent intuitive design.
You can read more about why we actually started building ZenML at our [blog](https://blog.maiot.io/why-zenml/).
