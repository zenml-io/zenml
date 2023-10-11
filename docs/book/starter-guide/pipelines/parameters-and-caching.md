---
description: Iteration is native to ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Quickly iterating in ZenML

Machine learning pipelines are rerun many times over throughout their development lifecycle. 

## Parameterizing steps

In order to iterate quickly, one must be able to quickly tweak pipeline runs by changing various 
parameters for the steps that make up your pipeline.

You can configure your pipelines at runtime in the following ways:

- `BaseParameters`: Runtime configuration passed down to steps as parameters.
- `BaseSettings`: Runtime settings passed down to stack components and pipelines.

In this section, we will focus on `BaseParameters`, and in the Advanced Guide we will 
[dive deeper into `BaseSettings`](../../advanced-guide/pipelines/pipelines.md).

You can parameterize a step by creating a subclass of the `BaseParameters`. When such a 
config object is passed to a step, it is not treated like other artifacts. Instead, it 
gets passed into the step when the pipeline is instantiated.

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step, BaseParameters


class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001


@step
def svc_trainer(
    params: SVCTrainerParams,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=params.gamma)
    model.fit(X_train, y_train)
    return model
```

The default value for the `gamma` parameter is set to `0.001`. However, when
the pipeline is instantiated you can override the default like this:

```python
first_pipeline_instance = first_pipeline(
    step_1=digits_data_loader(),
    step_2=svc_trainer(SVCTrainerParams(gamma=0.01)),
)

first_pipeline_instance.run()
```

{% hint style="info" %}
Behind the scenes, `BaseParameters` is implemented as a 
[Pydantic BaseModel](https://pydantic-docs.helpmanual.io/usage/models/).
Therefore, any type that 
[Pydantic supports](https://pydantic-docs.helpmanual.io/usage/types/)
is also supported as an attribute type in the `BaseParameters`.
{% endhint %}

Try running the above pipeline, and changing the parameter `gamma` through many runs. 
In essence, each pipeline can be viewed as an experiment, and each run is a trial of 
the experiment, defined by the `BaseParameters`. You can always get the parameters again 
when you [fetch pipeline runs](./fetching-pipelines.md), to compare various runs.

## Caching in ZenML

When you tweaked the `gamma` variable above, you must have noticed that the 
`digits_data_loader` step does not re-execute for each subsequent run.  This is because ZenML 
understands that nothing has changed between subsequent runs, so it re-uses the output of the last 
run (the outputs are persisted in the [artifact store](../../component-gallery/artifact-stores/artifact-stores.md). 
This behavior is known as **caching**.

Prototyping is often a fast and iterative process that
benefits a lot from caching. This makes caching a very powerful tool.
Checkout this [ZenML Blogpost on Caching](https://blog.zenml.io/caching-ml-pipelines/)
for more context on the benefits of caching and 
[ZenBytes lesson 1.2](https://github.com/zenml-io/zenbytes/blob/main/1-2_Artifact_Lineage.ipynb)
for a detailed example on how to configure and visualize caching.

ZenML comes with caching enabled by default. Since ZenML automatically tracks
and versions all inputs, outputs, and parameters of steps and pipelines, ZenML
will not re-execute steps within the same pipeline on subsequent pipeline runs
as long as there is no change in these three.

{% hint style="warning" %}
Currently, the caching does not automatically detect changes within the file
system or on external APIs. Make sure to set caching to `False` on steps that
depend on external inputs or if the step should run regardless of caching.
{% endhint %}


### Configuring caching behavior of your pipelines

Although caching is desirable in many circumstances, one might want to disable
it in certain instances. For example, if you are quickly prototyping with
changing step definitions or you have an external API state change in your
function that ZenML does not detect.

There are multiple ways to take control of when and where caching is used:
- [Disabling caching for the entire pipeline](#disabling-caching-for-the-entire-pipeline):
Do this if you want to turn off all caching (not recommended).
- [Disabling caching for individual steps](#disabling-caching-for-individual-steps):
This is required for certain steps that depend on external input.
- [Dynamically disabling caching for a pipeline run](#dynamically-disabling-caching-for-a-pipeline-run):
This is useful to force a complete rerun of a pipeline.

#### Disabling caching for the entire pipeline

On a pipeline level the caching policy can be set as a parameter within the decorator. 

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

{% hint style="info" %}
If caching is explicitly turned off on a pipeline level, all steps are run 
without caching, even if caching is set to `True` for single steps.
{% endhint %}

#### Disabling caching for individual steps

Caching can also be explicitly turned off at a step level. You might want to turn off caching for steps that take 
external input (like fetching data from an API or File IO).

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
```

{% hint style="info" %}
You can get a graphical visualization of which steps were cached using
the [ZenML Dashboard](./pipelines.md).
{% endhint %}

#### Dynamically disabling caching for a pipeline run

Sometimes you want to have control over caching at runtime instead of defaulting to the backed in configurations of 
your pipeline and its steps. ZenML offers a way to override all caching settings of the pipeline at runtime.

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

### Code Example

The following example shows caching in action with the code example from the
previous section.

For a more detailed example on how caching is used at ZenML and how it works
under the hood, checkout 
[ZenBytes lesson 1.2](https://github.com/zenml-io/zenbytes/blob/main/1-2_Artifact_Lineage.ipynb)!

<details>
<summary>Code Example of this Section</summary>

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.steps import BaseParameters, Output, step
from zenml.pipelines import pipeline


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


class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001


@step(enable_cache=False)  # never cache this step, always retrain
def svc_trainer(
    params SVCTrainerParams,
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

# Step one will use cache, step two will rerun due to the decorator config
first_pipeline_instance.run()

# The complete pipeline will be rerun
first_pipeline_instance.run(enable_cache=False)
```

#### Expected Output Run 1:

```
Creating run for pipeline: first_pipeline
Cache enabled for pipeline first_pipeline
Using stack default to run pipeline first_pipeline...
Step digits_data_loader has started.
Step digits_data_loader has finished in 0.135s.
Step svc_trainer has started.
Step svc_trainer has finished in 0.109s.
Pipeline run first_pipeline-07_Jul_22-12_05_54_573248 has finished in 0.417s.
```

#### Expected Output Run 2:

```
Creating run for pipeline: first_pipeline
Cache enabled for pipeline first_pipeline
Using stack default to run pipeline first_pipeline...
Step digits_data_loader has started.
Using cached version of digits_data_loader.
Step digits_data_loader has finished in 0.014s.
Step svc_trainer has started.
Step svc_trainer has finished in 0.051s.
Pipeline run first_pipeline-07_Jul_22-12_05_55_813554 has finished in 0.161s.
```

#### Expected Output Run 3:

```
Creating run for pipeline: first_pipeline
Cache enabled for pipeline first_pipeline
Using stack default to run pipeline first_pipeline...
Runtime configuration overwriting the pipeline cache settings to enable_cache=False for this pipeline run. The default caching strategy is retained for future pipeline runs.
Step digits_data_loader has started.
Step digits_data_loader has finished in 0.078s.
Step svc_trainer has started.
Step svc_trainer has finished in 0.048s.
Pipeline run first_pipeline-07_Jul_22-12_05_56_718489 has finished in 0.219s.
```

</details>
