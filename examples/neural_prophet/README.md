# 🔮 Predicting the future with NeuralProphet

[NeuralProphet](https://github.com/ourownstory/neural_prophet) is a Neural Network based Time-Series model, inspired
by [Facebook Prophet](https://github.com/facebook/prophet) and [AR-Net](https://github.com/ourownstory/AR-Net), built on
PyTorch. NeuralProphet bridges the gap between traditional time-series models and deep learning methods.

This example showcases how to train a `NeuralProphet` model in a ZenML pipeline. The ZenML `NeuralProphet` integration
includes a custom materializer that persists the trained `NeuralProphet` model to and from the artifact store. Here, we
utilize this materializer to train a model to predict the electricity consumption of a hospital.

The data used in this example is
available [here](https://colab.research.google.com/github/ourownstory/neural_prophet/blob/main/tutorials/application-example/energy_hospital_load.ipynb#scrollTo=0VKninwPyGl9)
and the pipeline is loosely based on this [guide](https://neuralprophet.com/html/energy_hospital_load.html) from the
NeuralProphet documentation.

## 🖥 Run it locally

## ⏩ SuperQuick `neural prophet` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run neural_prophet
```

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install neural_prophet -y

# pull example
zenml example pull neural_prophet
cd zenml_examples/neural_prophet

# Initialize ZenML repo
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```shell
python run.py
```

After running the pipeline, you may inspect the accompanying notebook to visalize results:

```shell
jupyter notebook
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
