# ⏭ Get interactive pipeline alerts with Slack and ZenML


This example showcases how to train a `XGBoost Booster` model in a ZenML pipeline. The ZenML `XGBoost` integration
includes a custom materializer that persists the trained `xgboost.Booster` model to and from the artifact store. It also
includes materializers for the custom `XGBoost.DMatrix` data object.

The data used in this example is the quickstart XGBoost data and is available in
the [demo directory of the XGBoost repository](https://github.com/dmlc/xgboost/tree/master/demo/data).

## 🖥 Run it locally

## ⏩ SuperQuick `xgboost` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run slack_alert
```

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install xgboost slack -y

# pull example
zenml example pull slack_alert
cd zenml_examples/slack_alert

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
