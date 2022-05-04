# 🏎 Explore Drift Detection
Data drift is something you often want to guard against in your pipelines.
Machine learning pipelines are built on top of data inputs, so it is worth
checking for drift if you have a model that was trained on a certain
distribution of data.

## 🗺 Overview
This example uses [`evidently`](https://github.com/evidentlyai/evidently), a
useful open-source library to painlessly check for data drift (among other
features). At its core, Evidently's drift detection takes in a reference data
set and compares it against another comparison dataset. These are both input in
the form of a `pandas` dataframe, though CSV inputs are also possible. You can receive these results in the form of a standard dictionary object containing all the relevant information, or as a visualization. We support both outputs.

ZenML implements this functionality in the form of several standardized steps.
You select which of the profile sections you want to use in your step by passing
a string into the `EvidentlyProfileConfig`. Possible options supported by
Evidently are:

- "datadrift"
- "categoricaltargetdrift"
- "numericaltargetdrift"
- "classificationmodelperformance"
- "regressionmodelperformance"
- "probabilisticmodelperformance"

## 🧰 How the example is implemented
In this example, we compare two separate slices of the same dataset as an easy
way to get an idea for how `evidently` is making the comparison between the two
dataframes. We chose [the University of Wisconsin breast cancer diagnosis
dataset](https://archive.ics.uci.edu/ml/datasets/Breast+Cancer+Wisconsin+(Diagnostic))
to illustrate how it works.

```python
from zenml.integrations.evidently.steps import (
    EvidentlyProfileConfig,
    EvidentlyProfileStep,
)

# instead of defining the step yourself, we have done it for you
drift_detector = EvidentlyProfileStep(
    EvidentlyProfileConfig(
        column_mapping=None,
        profile_section="datadrift",
    )
)
```

Here you can see that defining the step is extremely simple using our
class-based interface, and then you just have to pass in the two dataframes for
the comparison to take place.

We even allow you to use the Evidently visualization tool easily to display data
drift diagrams in your browser or within a Jupyter notebook:

![Evidently drift visualization UI](assets/drift_visualization.png)

# ☁️ Run in Colab
If you have a google account, you can get started directly with google colab - [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/evidently_drift_detection/evidently.ipynb)

# 🖥 Run it locally

## ⏩ SuperQuick `evidently` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run evidently_drift_detection
```

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install evidently
zenml integration install sklearn

# pull example
zenml example pull drift_detection
cd zenml_examples/drift_detection

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

Our docs regarding the evidently integration can be found [here](TODO: Link to docs).

If you want to learn more about visualizers in general or about how to build your own visualizers in zenml
check out our [docs](TODO: Link to docs)