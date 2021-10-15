<div align="center">

<img src="https://zenml.io/assets/social/github.svg">

<p align="center">
  <a href="https://zenml.io">Website</a> •
  <a href="https://docs.zenml.io">Docs</a> •
  <a href="https://zenml.io/roadmap">Roadmap</a> •
  <a href="https://zenml.io/discussion">Vote For Features</a> •
  <a href="https://zenml.io/slack-invite/">Join Slack</a>
</p>

[![PyPI - ZenML Version](https://img.shields.io/pypi/v/zenml.svg?label=pip&logo=PyPI&logoColor=white)](https://pypi.org/project/zenml/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenml)](https://pypi.org/project/zenml/)
[![PyPI Status](https://pepy.tech/badge/zenml)](https://pepy.tech/project/zenml)
![GitHub](https://img.shields.io/github/license/zenml-io/zenml)
[![Codecov](https://codecov.io/gh/zenml-io/zenml/branch/main/graph/badge.svg)](https://codecov.io/gh/zenml-io/zenml)
[![Interrogate](docs/interrogate.svg)](https://interrogate.readthedocs.io/en/latest/)
![Main Workflow Tests](https://github.com/zenml-io/zenml/actions/workflows/main.yml/badge.svg)

</div>

<div align="center"> Join our
<a href="https://zenml.io/slack-invite" target="_blank">
    <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
<b>Slack Community</b> </a> and become part of the ZenML family
</div>
<div align="center"> Give us a 
    <img width="25" src="https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png" alt="Slack"/>
<b>GitHub star</b> to show your love
</div>
<div align="center"> 
    <b>NEW: </b> <a href="https://zenml.io/discussion" target="_blank"><img width="25" src="https://cdn1.iconfinder.com/data/icons/social-17/48/like-512.png" alt="Vote"/><b> Vote</b></a> on the next ZenML features 
</div>

## What is ZenML?

**ZenML** is an extensible, open-source MLOps framework to create production-ready machine learning pipelines. It has a simple, flexible syntax, 
is cloud and tool agnostic, and has interfaces/abstractions that are catered towards ML workflows.

At its core, ZenML  pipelines execute ML-specific workflows from sourcing data to splitting, preprocessing, training, all the way to the evaluation of 
results and even serving. There are many built-in batteries as things progress in ML development. ZenML is not here to replace the great tools that 
solve these individual problems. Rather, it integrates natively with many popular ML tooling, and gives standard abstraction to write your workflows.

## Why do I need it?

_**Ichi Wa Zen, Zen Wa Ichi.**_

We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment.
ZenML follows the paradigm of [`Pipelines As Experiments` (PaE)](https://docs.zenml.io/why/why-zenml#pipelines-as-experiments-pae), meaning ZenML pipelines are designed to be written early on the development lifecycle, where the users can explore their 
pipelines as they develop towards production.

By using ZenML at the early stages of development, you get the following features:

* **Reproducibility** of training and inference workflows.
* Managing ML **metadata**, including versioning data, code, and models.
* Getting an **overview** of your ML development, with a reliable link between training and deployment.
* Maintaining **comparability** between ML models.
* **Scaling** ML training/inference to large datasets.
* Retaining code **quality** alongside development velocity. 
* **Reusing** code/data and reducing waste.
* Keeping up with the **ML tooling landscape** with standard abstractions and interfaces.


## Who is it for?
ZenML is built for ML practitioners who are ramping up their ML workflows towards production. 
It is created for data science / machine learning teams that are engaged in not only training models, but also putting them out in production. Production can mean many things, but examples would be:

* If you are using a model to generate analysis periodically for any business process.
* If you are using models as a software service to serve predictions and are consistently improving the model over time.
* If you are trying to understand patterns using machine learning for any business process.

* In all of the above, there will be team that is engaged with creating, deploying, managing and improving the entire process. You always want the best results, the best models, and the most robust and reliable results. This is where ZenML can help.
In terms of user persona, ZenML is created for producers of the models. This role is classically known as 'data scientist' in the industry and can range from research-minded individuals to more engineering-driven people. The goal of ZenML is to enable these practitioners to own their models until deployment and beyond.


## Release 0.5.0 and what lies ahead
The current release is bare bones (as it is a complete rewrite).
We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

* Standard interfaces for `TrainingPipeline`.
* Individual step interfaces like `PreprocesserStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
be included in the non-RC version of this release.
* A proper production setup with an orchestrator like Airflow.
* A post-execution workflow to analyze and inspect pipeline runs.
* The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
* Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
* Dependency management including Docker support is planned.

However, bare with us: Adding those features back in should be relatively faster as we now have a solid foundation to build on. Look out for the next email!


## Roadmap and Community
ZenML is being built in public. The [roadmap](https://zenml.io/roadmap) is a regularly updated source of truth for the ZenML community to understand where the product is going in the short, medium, and long term.

ZenML is managed by a [core team](https://zenml.io/team) of developers that are responsible for making key decisions and incorporating feedback from the community. The team oversee's feedback via various channels, but you can directly influence the roadmap as follows:

- Vote on your most wanted feature on the [Discussion board](https://zenml.io/discussion).
- Create a [Feature Issue](https://github.com/zenml-io/zenml/issues/new?assignees=&labels=&template=enhancement_request.md&title=%5BFEATURE%5D) in the [GitHub board](https://github.com/zenml-io/zenml/issues).
- Start a thread in the [Slack channel](https://zenml.io/slack-invite).

## Contributing

We would love to receive your contributions! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how best to contribute.

## Copyright

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository.

Any contribution made to this project will be licensed under the Apache License Version 2.0.

## Credit

ZenML is built on the shoulders of giants: we leverage, and would like to give credit to, existing open-source libraries like [TFX](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher-level interface with the focus being purely on easy-of-use and coherent intuitive design.
You can read more about why we actually started building ZenML at our [blog](https://blog.zenml.io/why-zenml/).

## Legacy [Updated Soon Q4 2021]
From this point onwards, the README is intended to give a glimpse as to what lies ahead. We have redesigned our [public roadmap](https://zenml.io/roadmap) 
to showcase better the timeline in which these features will be complete.

## Quickstart

The quickest way to get started is to create a simple pipeline.

#### Step 0: Installation

ZenML is available for easy installation into your environment via PyPI:

```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge:
**NOTE:** Do so on your own risk, no guarantees given!

```bash
pip install git+https://github.com/zenml-io/zenml.git@main --upgrade
```

#### Step 1: Initialize a ZenML repo from within a git repo

```bash
git init
zenml init
```

#### Step 2: Assemble, run and evaluate your pipeline locally

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.split import RandomSplit
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.trainer import TFFeedForwardTrainer


@step.trainer
def TFFeedForwardTrainer():
    pass

@pipeline(name="my_pipeline")
def SplitPipeline(simple_step: Step[SimplestStepEver],
                  data_step: Step[DataIngestionStep],
                  split_step: Step[DistSplitStep],
                  preprocesser_step: Step[InMemPreprocesserStep]):
    data_step(input_random_number=simple_step.outputs["return_output"])
    split_step(input_artifact=data_step.outputs["output_artifact"])
    preprocesser_step(input_artifact=split_step.outputs["output_artifact"])


pipeline = TrainingPipeline(
    data_step=ImportDataStep(uri='gs://zenml_quickstart/diabetes.csv'),
    split_step=RandomSplit(split_map={'train': 0.7, 'test': 0.3}),
    preprocesser_step=StandardPreprocesser(),
    trainer_step=TFFeedForwardTrainer(),
    evaluator_step=TFMAEvaluator()
)

# Run the pipeline locally
pipeline.run()
```

## Leverage powerful integrations

Once code is organized into a ZenML pipeline, you can supercharge your ML development with powerful integrations and 
on multiple [MLOps stacks].

### Work locally but switch seamlessly to the cloud

Switching from local experiments to cloud-based pipelines doesn't need to be complex.

```
pipeline.run('airflow_gcp_stack')
```

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
pipeline.view_schema()
```

![Automatic schema dection](docs/schema.png)

### View statistics

```python
# See statistics of train and eval
pipeline.view_statistics()
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

### Deploy models automatically

Automatically deploy each model with powerful Deployment integrations like [Cortex](examples/cortex).

```python
pipeline.add_deployment(
    CortexDeployerStep(
        api_spec=api_spec,
        predictor=PythonPredictor,
    )
)
```

The best part is that ZenML is extensible easily, and can be molded to your use-case. You can create your own custom logic or create a PR and contribute to the ZenML community, so that everyone can benefit.
