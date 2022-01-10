# Explore Drift Detection

Data Drift is something you often want to guard against in your pipelines.
Machine learning pipelines are built on top of data inputs, so it is worth
checking for drift if you have a model that was trained on a certain
distribution of data.

This example uses [`evidently`](https://github.com/evidentlyai/evidently), a
useful open-source library to painlessly check for data drift (among other
features). At its core, Evidently's drift detection takes in a reference data
set and compares it against another comparison dataset. These are both input in
the form of a `pandas` dataframe, though CSV inputs are also possible.

ZenML implements this functionality in the form of several standardized steps,
the first of which we use in the example:

- `EvidentlyDriftDetectionStep`
- `EvidentlyNumericalTargetDriftDetectionStep`
- `EvidentlyCategoricalTargetDriftDetectionStep`
- `EvidentlyClassificationModelPerformanceStep`
- `EvidentlyRegressionModelPerformanceStep`
- `EvidentlyProbabilisticModelPerformanceStep`

## How the example is implemented

In this example, we compare two separate slices of the same dataset as an easy
way to get an idea for how `evidently` is making the comparison between the two
dataframes. We chose [the University of Wisconsin breast cancer diagnosis
dataset](https://archive.ics.uci.edu/ml/datasets/Breast+Cancer+Wisconsin+(Diagnostic))
to illustrate how it works.

```python
# ... other imports
from zenml.integrations.evidently import steps as evidently_steps

# ... data loader and separate steps to get our full and partial dataframes

drift_detector = evidently_steps.EvidentlyDriftDetectionStep(
    evidently_steps.EvidentlyDriftDetectionConfig(column_mapping=None)
)

@pipeline
def drift_detection_pipeline(data_loader, full_data, partial_data, drift_detector):
    data_loader = data_loader()
    full_data = full_data(data_loader)
    partial_data = partial_data(data_loader)
    drift_detector(reference_dataset=full_data, comparison_dataset=partial_data)

pipeline = drift_detection_pipeline(
    data_loader=data_loader(),
    full_data=full_split(),
    partial_data=partial_split(),
    drift_detector=drift_detector,
)

pipeline.run()
```

Here you can see that defining the step is extremely simple using our
class-based interface and then you just have to pass in the two dataframes for
the comparison to take place.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations for this example
zenml integration install drift_detection

# pull example
zenml example pull drift_detection
```

### Run the project
Now we're ready. Execute:

```shell
zenml example run drift_detection
```

### Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
