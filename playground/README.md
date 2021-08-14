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
![GitHub](https://img.shields.io/github/license/zenml-io/zenml)
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

_**Ichi Wa Zen, Zen Wa Ichi.**_

This is the ZenML playground, home to the new redesign of ZenML. We are working on the following big features in this part of the 
repo:

* Creating easier abstractions with a complete redesign of how pipelines, steps, datasources and other first class components are created, with a focus on a functional design pattern.
* Focusing on developer experience in a Jupyter notebook.
* Getting rid of excess dependencies and making ZenML lightweight.
* Making ZenML more flexible to custom pipelines and ML use-cases.
* Making it easier to analyze and explore results and artifacts produced by ZenML pipelines.

In order to start with the playground, we have our `run.py` script. Install the requirements specified in the [requirements.txt](requirements.txt) and 
play around!

## Steps
Steps are now created as functions, with a simple annotation.

```python
@step
def PreprocesserStep(input_data: Input[CSVArtifact],
                     output_data: Output[CSVArtifact],
                     param: Param[float]):
    data = input_data.read()
    param = None
    output_data.write(data)
```

There will also be a distributed version of this annotation to easily write distributable steps.

## Pipelines
Pipelines are also created as functions, and will be in charge of connecting steps together:

```python
@SimplePipeline
def SplitPipeline(datasource: Datasource[CSVDatasource],
                  split_step: Step[SplitStep],
                  preprocesser_step: Step[PreprocesserStep]):
    split_step(input_data=datasource)
    preprocesser_step(input_data=split_step.outputs.output_data)


# Pipeline
split_pipeline = SplitPipeline(
    datasource=CSVDatasource("local_test/data/data.csv"),
    split_step=SplitStep(split_map=0.6),
    preprocesser_step=PreprocesserStep(param=1.0)
)
```

## Artifacts
Artifacts are objects that encapuslate the data flowing through steps. They have easy `read` and `write` functions to 
persist on disk.

## Datasources
Datasources are almost like a specialized artifact but with different functions on top to explore different versions.
