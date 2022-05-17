# :running: Get up and running quickly

Build your first ML pipelines with ZenML.

You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :earth_americas: Overview

The goal of this quickstart is to give you a small sample of what ZenML can do. To do so, we will:
- Train a model on the Digits dataset, evaluate it, deploy it, and embed it in an inference pipeline,
- Automatically version, track, and cache data, models, and other artifacts,
- Track model hyperparameters and metrics in an experiment tracking tool,
- Measure and visualize train-test skew, training-serving skew, and data drift.

## :computer: Run Locally

### :page_facing_up: Prerequisites 
In order to run locally, install ZenML and pull this quickstart:

```shell
# install ZenML
pip install zenml

# pull this quickstart to zenml_examples/quickstart
zenml example pull quickstart
cd zenml_examples/quickstart
```

### :arrow_forward: Run the Code
Now we're ready to start. You have two options for running the quickstart locally:

Option 1 - Interactively explore the quickstart using Jupyter Notebook:
```bash
pip install notebook
jupyter notebook
# open notebooks/quickstart.ipynb
```

Option 2 - Execute the whole ML pipeline from a Python script:
```shell
python run.py
```

### :sponge: Clean up

In order to clean up, simply delete the examples folder we downloaded earlier:

```shell
rm -rf zenml_examples
```

## :bulb: Learn More

If you want to learn more about ZenML, then the [:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) 
are the perfect place for you to get started.

Already have an MLOps stack in mind? Whatever tools you plan on using,
ZenML most likely has 
[**:link: Integrations**](https://docs.zenml.io/features/integrations) for them already.
Check out the 
[**:pray: ZenML Examples**](https://github.com/zenml-io/zenml/tree/main/examples)
to see how to use a specific tool in ZenML.

If you would like to learn about the different MLOps concepts in more detail, check out
[**:teacher: ZenBytes**](https://github.com/zenml-io/zenbytes),
our series of short practical MLOps lessons.

Also, make sure to join our <a href="https://zenml.io/slack-invite" target="_blank">
    <img width="15" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!