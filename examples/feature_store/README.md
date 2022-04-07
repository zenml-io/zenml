# 🗂 Get your data from a Feature Store

basic introduction paragraph
- what is a feature store
- what problem does it solve
- what specific combo have we integrated with?

## 🗺 Overview: Features Stores & ZenML

- how to think about a feature store
- what is it used for?
- components / architecture of a feature store
	- offline / batch serving
	- online serving
- The main abstractions you need to think of / how do we help you?:
	- getting offline features
	- getting online features
- caveats about our integration
	- this example runs locally
	- we assume you have a feature store already if you want to use it in production (ZenML doesn't currently help you set that all up)
	- online serving doesn't work in tandem with deployed models currently
- This example, and what features of features it showcases / what you can do with the ZenML feature store integration

## 🧰 How the example is implemented

Showcase the code and explain how it works
(Maybe a visual diagram showing the various parts of it?

# 🖥 Run it locally

## ⏩ SuperQuick `feature-store` run

If you're really in a hurry, and you want just to see this example pipeline run, without wanting to fiddle around with all the individual installation and configuration steps, just run the following:

```shell
zenml example run feature_store
```

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integration
zenml integration install feast

# pull example
zenml example pull feature_store
cd zenml_examples/feature_store

# Initialize ZenML repo
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the Feast feature store integration can be found [here](TODO: Link to docs).
