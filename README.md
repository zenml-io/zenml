<div align="center">

<img src="https://zenml.io/assets/social/github.svg">

---

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

---

<div> Please join our
<a href="https://zenml.io/slack-invite" target="_blank">
    <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
<b>Slack Community</b> </a> to be the first to get involved in the ZenML community
</div>

---

## What is ZenML?
**ZenML** is an extensible, open-source MLOps framework for using production-ready Machine Learning pipelines - in a simple way. The key features of ZenML are:

* Guaranteed reproducibility of your training experiments. Your pipelines are versioned from data to model, experiments automatically tracked and all pipeline configs are declarative by default.
* Guaranteed comparability between experiments.
* Ability to quickly switch between local and cloud environments (e.g. Kubernetes, Apache Beam).
* Built-in and extensible abstractions for all MLOps needs - from distributed processing on large datasets to Cloud-integrations and model serving backends.
* Pre-built helpers to compare and visualize input parameters as well as pipeline results (e.g. Tensorboard, TFMA, TFDV).
* Cached pipeline states for faster experiment iterations.

**ZenML** is built to take your experiments all the way from data versioning to a deployed model. It replaces fragile glue-code and scripts to automate Jupyter Notebooks for **production-ready Machine Learning**. The core design is centered around **extensible interfaces** to accommodate **complex pipeline** scenarios, while providing a **batteries-included, straightforward “happy path”** to achieve success in common use-cases **without unnecessary boiler-plate code**.

### Contents

* [Quickstart](#quickstart)
* [Installation](#step-0-installation)
* [ZenML Concepts](#zenml-concepts)
* [Community](#community)
* [Contributing](#contributing)
* [Copyright](#copyright)
* [Credit](#credit)
* [Citation](#citation)


## Quickstart 

If you're more of a visual learner, you can also watch the [quickstart video](https://www.youtube.com/watch?v=Stg5rA_0oa8) where the below is explained in more depth.

Let’s get you started with a simple pipeline. Please make sure to also check out the [advanced concepts](#zenml-concepts). It uses some built-ins and a very simple model. 
The dataset used is the [Pima Indians Diabetes Dataset](https://storage.googleapis.com/zenml_quickstart/diabetes.csv), originally from the National Institute of Diabetes 
and Digestive and Kidney Diseases. It is a binary classification problem.


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
from zenml.core.steps.preprocesser.standard_preprocesser.standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.feedforward_trainer import FeedForwardTrainer

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

#### Step 3: Leverage powerful integrations
```python
# See schema of data
training_pipeline.view_schema()

# See statistics of train and eval
training_pipeline.view_statistics()

# Creates a notebook for evaluation
training_pipeline.evaluate()
```

Of course, each of these steps can be [extended quite easily](https://docs.zenml.io/steps/creating-custom-steps) to accommodate more complex scenarios and use-cases. There is a steadily-growing number of integrations available, 
for example Google Dataflow for [distributed preprocessing](https://docs.zenml.io/backends/processing-backends) or Google Cloud AI Platform as a 
[training](https://docs.zenml.io/backends/training-backends) backend. 

You can also run these pipelines on a cloud VM, for example on a Google Cloud Platform VM, [with a few more lines of code](https://docs.zenml.io/tutorials/running-a-pipeline-on-a-google-cloud-vm).

## ZenML Concepts

At its core, ZenML will orchestrate your experiment pipelines from **sourcing data** to **splitting, preprocessing, training**, all the way to the **evaluation of results** and even **serving**.

While there are other pipelining solutions for Machine Learning experiments, ZenML is focussed on two unique approaches:

* Reproducibility.
* Integrations.

Let us introduce some of the concepts we use to make this focus a reality.
### Reproducibility

ZenML is built with reproducibility in mind. Reproducibility is a core motivation of DevOps methodologies: Builds need to be reproducible. Commonly, this is achieved by version control of code, version pinning of dependencies and automation of workflows. ZenML bundles these practises into a coherent framework for Machine Learning.
Machine Learning brings an added level of complexity to version control, beyond versioning code: Data is inherently hard to version. 
#### Versioning of data
ZenML takes an easy, yet effective approach to version controlling data. When sourcing data, either via dedicated data pipelines or within your training pipelines, ZenML creates an immutable snapshot of the data (TFRecords) used for your specific pipeline. This snapshot is tracked, just like any other pipeline step, and becomes available as a starting point to subsequent pipelines when using the same parameters for sourcing data.

**NOTE:** The principles behind versioning data in ZenML is a variation of the method used for caching pipeline steps.
#### Versioning of code
It is not necessary to reinvent the wheel when it comes to version control of code - chances are, you’re already using git to do so (and if not, you should). ZenML can tap into a repository's history and allow for version-pinning of your own code via git SHA’s. 

This becomes exceptionally powerful when you have code you want / need to embed at serving time, as there is now not just lineage of data, but also lineage of code from experiment to serving.
#### Declarative configuration
Declarative configurations are a staple of DevOps methodologies, ultimately brought to fame through [Terraform](https://terraform.io). In a nutshell: A pipeline’s configuration declares the “state” the pipeline should be in and the processing that should be applied, and ZenML figures out where the code lies and what computations to apply.

That way, when your teammate clones your repo and re-runs a pipeline config on a different environment, the pipeline remains reproducible. 
#### Metadata Tracking
While versioning and declarative configs are essential for reproducibility, there needs to be a system that keeps track of all processes as they happen. Google’s [ML Metadata](https://github.com/google/ml-metadata) standardizes metadata tracking, and makes it easy to keep track of iterative experimentation as it happens. ZenML uses ML Metadata extensively (natively as well as via the TFX interface) to automatically track all **relevant** parameters that are created through ZenML pipeline interfaces. This not only helps in post-training workflows to compare results as experiments progress, but also has the added advantage of leveraging caching of pipeline steps.
### Integrations

The Machine Learning landscape is evolving at a rapid pace. We’re decoupling your experiment workflow from the tooling by providing integrations to solutions for specific aspects of your ML pipelines.

#### Metadata and Artifacts

With ZenML, inputs and outputs are tracked for every pipeline step. Output artifacts (e.g. binary representations of data, splits, preprocessing results, models) are centrally stored and are automatically used for caching. To facilitate that, ZenML relies on a Metadata Store and an Artifact Store.

By default, both will point to a subfolder of your local `.zenml` directory, which is created when you run `zenml init`. It’ll contain both the Metadata Store (default: SQLite) as well as the Artifact Store (default: tf.Records in local folders).

More advanced configurations might want to centralize both the Metadata as well as the Artifact Store, for example for use in Continuous Integration or for collaboration across teams:

The Metadata Store can be simply configured to use any MySQL server (=>5.6):
```bash
zenml config metadata set mysql \
    --host 127.0.0.1 \ 
    --port 3306 \
    --username USER \
    --passwd PASSWD \
    --database DATABASE
```

The Artifact Store offers native support for Google Cloud Storage:
```bash
zenml config artifacts set gs://your-bucket/sub/dir
```

<!-- INSERT INFO ABOUT EXTENDING METADATA AND ARTIFACT STORE INTERFACES -->

#### Orchestration
As ZenML is centered on decoupling workflow from tooling we provide a growing number of out-of-the-box supported backends for orchestration. 

When you configure an orchestration backend for your pipeline, the environment you execute actual `pipeline.run()` will launch all pipeline steps at the configured orchestration backend, not the local environment. ZenML will attempt to use credentials for the orchestration backend in question from the current environment.
**NOTE:** If no further pipeline configuration if provided (e.g. processing or training backends), the orchestration backend will also run all pipeline steps.

A quick overview of the currently supported backends:

| **Orchestrator** 	| **Status** 	|
|-	|-	|
| Google Cloud VMs 	| >0.1 	|
| Kubernetes 	| Q1/2021 	|
| Kubeflow 	| WIP 	|

Integrating custom orchestration backends is fairly straightforward. Check out our example implementation of [Google Cloud VMs](https://github.com/maiot-io/zenml/blob/main/zenml/core/backends/orchestrator/gcp/orchestrator_gcp_backend.py) to learn more about building your own integrations.

<!-- INSERT INFO ABOUT CONFIGURING ORCHESTRATION INTERFACES -->
<!-- INSERT LINK TO DOCS -->
#### Distributed Processing
Sometimes, pipeline steps just need more scalability than what your orchestration backend can offer. That’s when the natively distributable codebase of ZenML can shine - it’s straightforward to run pipeline steps on processing backends like Google Dataflow or Apache Spark. 

ZenML is using Apache Beam for it’s pipeline steps, therefore backends rely on the functionality of Apache Beam. A processing backend will execute all pipeline steps before the actual training.

Processing backends can be used to great effect in conjunction with an orchestration backend. To give a practical example: You can orchestrate your pipelines using Google Cloud VMs and configure to use a service account with permissions for Google Dataflow and Google Cloud AI Platform. That way you don’t need to have very open permissions on your personal IAM user, but can relay authority to service-accounts within Google Cloud.

We’re adding support for processing backends continuously:

| **Backend** 	| **Status** 	|
|-	|-	|
| Google Cloud Dataflow 	| >0.1 	|
| Apache Spark 	| WIP 	|
| AWS EMR 	| WIP 	|
| Flink 	| planned: Q3/2021 	|

<!-- INSERT EXAMPLE ABOUT CONFIGURING PROCESSING BACKENDS -->
<!-- INSERT LINK TO DOCS -->
#### Training
Many ML use-cases and model architectures require GPUs/TPUs. ZenML offers integrations to Cloud-based ML training offers, and provides a way to extend the training interface to allow for self-built training backends. 

Some of these backends rely on Docker containers or other methods of transmitting code. Please see the documentation for a specific training backend for further details. 

| **Backend** 	| **Status** 	|
|-	|-	|
| Google Cloud AI Platform 	| >0.1 	|
| AWS Sagemaker 	| WIP 	|
| Azure Machine Learning 	| planned: Q3/2021 	|

<!-- INSERT EXAMPLE ABOUT CONFIGURING TRAINING BACKENDS -->
<!-- INSERT LINK TO DOCS -->
#### Serving
Every ZenML pipeline yields a servable model, ready to be used in your existing architecture - for example as additional input for your CI/CD pipelines. To accommodate other architectures, ZenML has support for a growing number of dedicated serving backends, with clear linkage and lineage from data to deployment. 

| **Backend** 	| **Status** 	|
|-	|-	|
| Google Cloud AI Platform 	| >0.1 	|
| AWS Sagemaker 	| WIP 	|
| Seldon 	| planned: Q1/2021 	|
| Azure Machine Learning 	| planned: Q3/2021 	|

<!-- INSERT EXAMPLE ABOUT CONFIGURING SERVING BACKENDS -->
<!-- INSERT LINK TO DOCS -->

<!-- ## Comparison

<Align this with the ZenML landing page about competition, redo the analysis>
<This might very well be added at a later stage!>
-->

## Current limitations
Currently, ZenML only supports Tensorflow 2.3.0 based models. However, the vision of the framework is to be library and dependency agnostic.

Please see our [roadmap](https://docs.zenml.io/misc/roadmap) for details on how and when we plan to extend ZenML moving forward.

## Community
Our community is the backbone of making ZenML a success! We are currently actively maintaining two main channels for community discussions:

* Our Slack Channel: Chat with us [here](https://zenml.io/slack-invite/).
* The GitHub Community: Create your first thread [here](https://github.com/maiot-io/zenml/discussions).

## Contributing

We would love to receive your contribution! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how to contribute best.

## Copyright

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository.

Any contribution made to this project will be licensed under the Apache License Version 2.0.

## Credit

ZenML is built on the shoulders of giants: We leverage, and would like to give credit to, existing open-source libraries like [TFX](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher level interface with the focus being purely on easy-of-use and coherent intuitive design.
You can read more about why we actually started building ZenML at our [blog](https://blog.maiot.io/why-zenml/).


## Citation

If you want to cite the framework feel free to use this:

```
@article{maiotzenml,
  title={ZenML},
  author={maiot, Munich},
  journal={GitHub. Note: https://github.com/maiot-io/zenml},
  volume={1},
  year={2020}
}
```
