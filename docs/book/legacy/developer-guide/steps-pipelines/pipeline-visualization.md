---
description: How to visualize ZenML pipeline runs
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


ZenML's **Dash** integration provides a `PipelineRunLineageVisualizer` that can
be used to visualize pipeline runs in your local browser, as shown below:

![Pipeline Run Visualization Example](../../assets/developer-guide/pipeline-visualization/run2.png)

## Requirements

Before you can use the Dash visualizer, you first need to install ZenML's Dash
integration:

```shell
zenml integration install dash -y
```

{% hint style="info" %}
See the [Integrations](../../mlops-stacks/integrations.md) page for more
details on ZenML integrations and how to install and use them.
{% endhint %}

## Visualizing Pipelines

After a pipeline run has been started, we can access it using the 
post-execution utilities, as you learned in the last section on 
[Inspecting Finished Pipeline Runs](./inspecting-pipeline-runs.md).

We can then visualize a run using the `PipelineRunLineageVisualizer` class:

```python
from zenml.integrations.dash.visualizers.pipeline_run_lineage_visualizer import (
    PipelineRunLineageVisualizer,
)
from zenml.post_execution import get_pipeline


latest_run = get_pipeline(<PIPELINE_NAME>).runs[-1]
PipelineRunLineageVisualizer().visualize(latest_run)
```

This will open an interactive visualization in your local browser at 
`http://127.0.0.1:8050/`, where squares represent your artifacts and circles
your pipeline steps. 

{% hint style="info" %}
The different nodes are color-coded in the visualization, so if
your pipeline ever fails or runs for too long, you can find the responsible 
step at a glance, as it will be colored red or yellow respectively.
{% endhint %}

### Visualizing Caching

In addition to `Completed`, `Running`, and `Failed`, there is also a separate
`Cached` state. You already learned about caching in a previous section on
[Caching Pipeline Runs](./caching.md). Using the `PipelineRunLineageVisualizer`,
you can see at a glance which steps were cached (green) and which were rerun (blue).
See below for a detailed example.

## Code Example

In the following example we use the `PipelineRunLineageVisualizer` to visualize
the three pipeline runs from the [Caching Pipeline Runs Example](./caching.md#code-example):

<details>
<summary>Code Example of this Section</summary>

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.steps import BaseStepConfig, Output, step
from zenml.pipelines import pipeline

from zenml.integrations.dash.visualizers.pipeline_run_lineage_visualizer import (
    PipelineRunLineageVisualizer,
)


@step
def digits_data_loader() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset as a tuple of flattened numpy arrays."""
    digits = load_digits()
    data = digits.images.reshape((len(digits.images), -1))
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.2, shuffle=False
    )
    return X_train, X_test, y_train, y_test


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


@step(enable_cache=False)  # never cache this step, always retrain
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model


@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)


first_pipeline_instance = first_pipeline(
    step_1=digits_data_loader(),
    step_2=svc_trainer()
)


# The pipeline is executed for the first time, so all steps are run.
first_pipeline_instance.run()
latest_run= first_pipeline_instance.get_runs()[-1]
PipelineRunLineageVisualizer().visualize(latest_run)

# Step one will use cache, step two will rerun due to the decorator config
first_pipeline_instance.run()
latest_run = first_pipeline_instance.get_runs()[-1]
PipelineRunLineageVisualizer().visualize(latest_run)

# The complete pipeline will be rerun
first_pipeline_instance.run(enable_cache=False)
latest_run = first_pipeline_instance.get_runs()[-1]
PipelineRunLineageVisualizer().visualize(latest_run)
```

### Expected Visualizations

#### Run 1:

![Visualization Run 1](../../assets/developer-guide/pipeline-visualization/run1.png)

#### Run 2:

![Visualization Run 2](../../assets/developer-guide/pipeline-visualization/run2.png)

#### Run 3:

![Visualization Run 3](../../assets/developer-guide/pipeline-visualization/run3.png)

</details>