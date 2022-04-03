# Caching in ZenML
Caching is an important feature of any machine learning pipeline. Through caching we make sure that the artifacts that 
a step produces can be reused in a consecutive pipeline run, thus saving time and energy. However it is important to 
understand how this caching works, how to disable it and when it is invalidated.

## 🗺 Overview

Within this tutorial you'll get a quick overview of caching in action. 

## ⚡ Get started immediately - [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/feature/ENG-634-beautify-examples/examples/caching/caching_in_zenml.ipynb)

We've written a notebook on caching that you can get started on immediately on [Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/feature/ENG-634-beautify-examples/examples/caching/caching_in_zenml.ipynb).

## 💻 Run it locally
### 📃 Pre-requisites

```shell
# install CLI
pip install zenml 

# pull example if you don't have it locally already
zenml example pull caching
cd zenml_examples/caching
```

### ▶ Run the code

We offer two ways for you to try this out locally:

1. Start the notebook server of your choice and dive right into the [code](caching_in_zenml.ipynb)

2. Try it in our [caching_in_zenml.py](caching_in_zenml.py) script 

```bash
python caching_in_zenml.py
```

This will run the same pipeline twice and showcase caching in ZenML. Read the logs in
your CLI to see how caching affects runtime and step execution.

### 👓 Learn more

Check out our [Docs](https://docs.zenml.io/features/caching) to  find more about caching and ZenML
