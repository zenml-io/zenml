# 🏃 Get up and running quickly

Get your first practical experiences with ZenML.

You can use Google Colab to see ZenML in action, no sign up / installation required!

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb)

## 🗺 Overview
We build an ML pipeline to train a simple sklearn classifier on the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset and deploy it...

The goal of this quickstart is just to give you a small sample of what ZenML can do.

## 🖥 Run Locally

### 📄 Prerequisites 
In order to run this exampl locally, install and initialize ZenML:

```shell
# install ZenML
pip install zenml

# install ZenML integrations
zenml integration install sklearn

# pull example
zenml example pull quickstart
cd zenml_examples/quickstart

# initialize
zenml init
```

### ▶️ Run the Code
Now we're ready. You have two options for running the quickstart locally:

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

### 🧽 Clean up

In order to clean up, simply delete the examples folder we fetched earlier:

```shell
rm -rf zenml_examples
```

## 📜 Learn more

If you want to learn more about ZenML, then the [**ZenML Docs**](https://docs.zenml.io/) 
are the perfect place for you to get started.

Already have an MLOps stack in mind? Whatever tools you plan on using,
ZenML most likely has 
[**Integrations**](https://docs.zenml.io/features/integrations) for them already.
Check out the 
[**ZenML Examples**](https://github.com/zenml-io/zenml/tree/main/examples)
to see how to use a specific tool in ZenML.

If you would like to learn about ZenML and MLOps through examples, check out
[**ZenBytes**](https://github.com/zenml-io/zenbytes),
our series of short practical MLOps lessons.

Also, make sure to join our <a href="https://zenml.io/slack-invite" target="_blank">
    <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!