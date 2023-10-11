---
description: How to track custom run metadata related to a stack component
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Certain stack components create dynamic, run-specific metadata that is
displayed in the dashboard together with each run, usually either for
convenience or reproducibility purposes. 
As an example, you might find a link to the orchestrator UI among the metadata 
of your pipeline runs, or the experiment tracker project name among the 
metadata of a specific step, depending on which stack component flavors you 
use.

## Base Abstraction

Which metadata is tracked is defined by two methods of the
[StackComponent base class](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/stack_component.py):
- `get_pipeline_run_metadata()` defines the metadata that is associated with 
an entire pipeline run (such as the orchestrator URL) and is called once at
the beginning of your pipeline run,
- `get_step_run_metadata()` defines step-specific metadata (such as the 
experiment tracker project name) and gets called after the respective step 
has finished running.

Below you can see the base class definitions of both methods:

```python
from zenml.config.step_run_info import StepRunInfo
from zenml.metadata.metadata_types import MetadataType


class StackComponent:

    ...

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        return {}

    ...

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        return {}
```

Both functions are expected to return dicts mapping names to the values you 
wish to track.
The only requirement is that all your values are built-in types (like `str`, 
`int`, `list`, `dict`, ...) or among the special types defined in
[src.zenml.metadata.metadata_types](https://github.com/zenml-io/zenml/blob/main/src/zenml/metadata/metadata_types.py)
that are displayed in a dedicated way in the dashboard.
See [src.zenml.metadata.metadata_types.MetadataType](https://github.com/zenml-io/zenml/blob/main/src/zenml/metadata/metadata_types.py)
for more details.

## Subclass Example (MLflow Tracking)

To track metadata, you need to override the two methods above to return dicts
of values that you wish to track for your pipeline and step runs respectively.
As an example, let us look at how these methods are implemented in the 
[MLflow experiment tracker](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/mlflow/experiment_trackers/mlflow_experiment_tracker.py):

```python
from zenml.config.step_run_info import StepRunInfo
from zenml.metadata.metadata_types import MetadataType, Uri


class MLFlowExperimentTracker(BaseExperimentTracker):

    ...

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        return {
            "mlflow_tracking_uri": Uri(self.get_tracking_uri()),
        }
    
    ...

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        return {
            "mlflow_run_id": mlflow.active_run().info.run_id,
            "mlflow_experiment_id": mlflow.active_run().info.experiment_id,
        }
```

As you see, the MLflow experiment tracker extracts the tracking URI on a 
pipeline level and both the run ID and experiment ID for each step where it was
used. All of these values are of type `str`, which is an allowed metadata type, 
so we can return them directly. However, we cast the tracking URI to type `Uri`
here to have it rendered as a link in the dashboard. 

{% hint style="info" %}
If your stack component should track a value that is not a built-in datatype 
(or otherwise part of `MetadataType`), you will need to cast it to a supported
datatype first. For example, if you had a value `x: numpy.float64`, you could
cast it to a built-in `float` type via `x.item()`. Or, if you wanted to track a 
custom class `y: CustomClass`, you could track its string representation 
`str(y)` instead.
{% endhint %}
