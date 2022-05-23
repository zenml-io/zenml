# ⏭ Gradient Boosting with LightGBM and ZenML

[LightGBM](https://lightgbm.readthedocs.io/en/latest/) is a gradient boosting framework that uses tree-based learning
algorithms. It is designed to be distributed and efficient with the following advantages:

- Faster training speed and higher efficiency.
- Lower memory usage.
- Better accuracy.
- Support for parallel, distributed, and GPU learning.
- Capable of handling large-scale data.

This example showcases how to train a `lightgbm.Booster` model in a ZenML pipeline. The ZenML LightGBM integration
includes a custom materializer that persists the trained `lightgbm.Booster` model to and from the artifact store. It
also includes materializers for the custom `LightGBM.Dataset` data object.

The data used in this example is the quickstart LightGBM data and is available in
the [simple python example of the LightGBM repository](https://github.com/microsoft/LightGBM/blob/master/examples/python-guide/simple_example.py)
.

## 🖥 Run it locally

## ⏩ SuperQuick `lightgbm` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install lightgbm -y

# pull example
zenml example pull lightgbm
cd zenml_examples/lightgbm

# initialize
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```shell
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

```shell
zenml example run lightgbm
```
