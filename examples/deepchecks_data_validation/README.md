# 🏎 Validate your data
Data validation is something you often want to include in your pipelines.
Machine learning pipelines are built on top of data inputs, so it is worth
checking the data to ensure it looks the way you want it to look.

## 🗺 Overview
This example uses [`deepchecks`](https://github.com/deepchecks/deepchecks), a
useful open-source library to painlessly do data validation. At its core, `deepchecks` 
data validation library takes in a reference data set and compares it against another comparison dataset. 
These are both input in the form of a `pandas` dataframe. You can receive these results in the form of a 
`SuiteResult` object that can in turn be visualized in a notebook or in the browser as a HTML webpage.


## 🧰 How the example is implemented
In this example, we compare two separate slices of the same dataset as an easy
way to get an idea for how `deepchecks` is making the comparison between the two
dataframes. We chose the Iris dataset.

```python

```

Here you can see that defining the step is extremely simple using our
class-based interface, and then you just have to pass in the two dataframes for
the comparison to take place.

We even allow you to use the Deepchecks visualization tool easily to display the 
report in your browser or within a Jupyter notebook:

![Deepchecks drift visualization UI](assets/drift_visualization.png)

# ☁️ Run in Colab
If you have a Google account, you can get started directly with Colab - [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/feature/ENG-634-beautify-examples/examples/deepchecks_drift_detection/deepchecks.ipynb)

# 🖥 Run it locally

## ⏩ SuperQuick `deepchecks` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run deepchecks_drift_detection
```

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install deepchecks sklearn

# pull example
zenml example pull deepchecks_data_validation
cd zenml_examples/deepchecks_data_validation

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

Our docs regarding the deepchecks integration can be found [here](TODO: Link to docs).

If you want to learn more about visualizers in general or about how to build your own visualizers in ZenML
check out our [docs](TODO: Link to docs)