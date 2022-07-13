---
description: Guard against data drift with our Evidently integration.
---

- `What is it, what does it do`
- `Why would you want to use it`
- `When should you start adding this to your stack`
- `Overview of flavors, tradeoffs, when to use which flavor (table)`

# Perform Drift Detection

Data drift is something you often want to guard against in your pipelines.
Machine learning pipelines are built on top of data inputs, so it is worth
checking for drift if you have a model that was trained on a certain
distribution of data. What follows is an example of how we use one drift
detection tool that ZenML has currently integrated with. This takes the form of
a standard step that you can use to make the relevant calculations.

## 🗺 Overview

[`Evidently`](https://github.com/evidentlyai/evidently) is a useful open-source library to painlessly check for data drift (among other features). At its core, Evidently's drift detection takes in a reference data set and compares it against another comparison dataset. These are both input in the form of a Pandas `DataFrame`, though CSV inputs are also possible. You can receive these results in the form of a standard dictionary object containing all the relevant information, or as a visualization. ZenML supports both outputs.

ZenML implements this functionality in the form of several standardized steps. You select which of the profile sections you want to use in your step by passing a string into the `EvidentlyProfileConfig`. Possible options supported by Evidently are:

* "datadrift"
* "categoricaltargetdrift"
* "numericaltargetdrift"
* "classificationmodelperformance"
* "regressionmodelperformance"
* "probabilisticmodelperformance"
* "dataquality" (NOT CURRENTLY IMPLEMENTED)

## 🧰 How to validate data inside a ZenML step

With Evidently, we compare two separate DataFrames. ZenML provides custom steps which you can set up for drift detection as in the following code:

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

Here you can see how to define the step using our class-based interface. 
Then you just have to pass in the two dataframes for the comparison to take place.

This could be done at the point when you are defining your pipeline:

```python
from zenml.integrations.constants import EVIDENTLY, SKLEARN
from zenml.pipelines import pipeline

@pipeline(required_integrations=[EVIDENTLY, SKLEARN])
def drift_detection_pipeline(
        data_loader,
        data_splitter,
        drift_detector,
        drift_analyzer,
):
    """Links all the steps together in a pipeline"""
    data = data_loader()
    reference_dataset, comparison_dataset = data_splitter(data)
    drift_report, _ = drift_detector(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    drift_analyzer(drift_report)
```

For the full context of this code, please visit our `drift_detection` example [here](https://github.com/zenml-io/zenml/tree/main/examples/evidently_drift_detection). The key part of the pipeline definition above is when we use the datasets derived from the `data_splitter` step (i.e. function) and pass them in as arguments to the `drift_detector` function as part of the pipeline.

We even allow you to use the Evidently visualization tool to display data drift diagrams in your browser or within a Jupyter notebook:

![Evidently drift visualization UI](../assets/evidently/drift_visualization.png)

Simple code like this would allow you to access the Evidently visualizer based on the completed pipeline run:

```python
from zenml.integrations.evidently.visualizers import EvidentlyVisualizer
from zenml.repository import Repository

repo = Repository()
pipe = repo.get_pipelines()[-1]
evidently_outputs = pipe.runs[-1].get_step(name="drift_detector")
EvidentlyVisualizer().visualize(evidently_outputs)
```
