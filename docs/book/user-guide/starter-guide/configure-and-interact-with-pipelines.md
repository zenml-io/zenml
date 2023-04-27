---
description: Learn how to configure steps, pipelines
---

# Create an ML Pipeline

In this section we build out the first ML pipeline. For this lets get the imports out of the way first:

```python
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.pipelines.new import pipeline
from zenml.steps import Output, step
```

## Multiple Outputs

Sometimes a step will have multiple outputs. In order to give each output a unique name, use the `Output()` Annotation. Here we load an open source dataset and split it into a train and a test dataset.

<pre class="language-python"><code class="lang-python"><strong>@step
</strong>def digits_data_loader() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset and splits it into train and test data."""
    # Load data from the digits dataset
    digits = load_digits()
    # transform these images into flattened numpy arrays
    data = digits.images.reshape((len(digits.images), -1))
    # split into datasets
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.2, shuffle=False
    )
    return X_train, X_test, y_train, y_test
</code></pre>

### Parametrize a Step

Here we are creating a training step for a support vector machine classifier with sklearn. As we might want to adjust the hyperparameter `gamma` later on, we define it as an input value to the step as well.

```python
@step
def svc_trainer(
    gamma: float = 0.001,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    
    # instantiate a support vector machine model    
    model = SVC(gamma=gamma)
    # Train on the train dataset
    model.fit(X_train, y_train)
    return model
```

{% hint style="info" %}
In case you want to run the step function outside the context of a ZenML pipeline, all you need to do is call the `.entrypoint()` method with the same input signature. For example:

```python
svc_trainer.entrypoint(X_train=..., y_train=...)
```
{% endhint %}

## Pipeline

Next, we will combine our two steps into a pipeline and run it. As you can see here, the parameter gamma is configurable as a pipeline input.&#x20;

```python
@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = step_1()
    step_2(gamma=gamma, X_train, y_train)
    
first_pipeline(gamma=0.0015)
```

Running it should look somewhat like this in the terminal.

<pre class="language-sh" data-line-numbers><code class="lang-sh">$python main.py
<strong>Registered new pipeline with name `first_pipeline`.
</strong>.
.
.
Pipeline run `first_pipeline-...` has finished in 0.236s.
</code></pre>

## Code Summary

<details>

<summary>All the code in one place</summary>

```python
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.pipelines.new import pipeline
from zenml.steps import Output, step

@step
def digits_data_loader() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset and splits it into train and test data."""
    # Load data from the digits dataset
    digits = load_digits()
    # transform these images into flattened numpy arrays
    data = digits.images.reshape((len(digits.images), -1))
    # split into datasets
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.2, shuffle=False
    )
    return X_train, X_test, y_train, y_test
    
@step
def svc_trainer(
    gamma: float = 0.001,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    
    # instantiate a support vector machine model    
    model = SVC(gamma=gamma)
    # Train on the train dataset
    model.fit(X_train, y_train)
    return model

@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = step_1()
    step_2(gamma=gamma, X_train, y_train)
    
first_pipeline(gamma=0.0015)
```

</details>

### Give each pipeline run a name

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current date and time as the name for the pipeline run. In order to change the name for a run, pass `run_name` as a parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or run them on a schedule, make sure to either compute the run name dynamically or include one of the following placeholders that will be replaced by ZenML:

* `{{date}}` will resolve to the current date, e.g. `2023_02_19`
* `{{time}}` will resolve to the current time, e.g. `11_07_09_326492`

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name_{{date}}_{{time}}")
```

Machine learning pipelines are rerun many times over throughout their development lifecycle.

## Caching in ZenML

When you tweaked the `gamma` variable above, you must have noticed that the `digits_data_loader` step does not re-execute for each subsequent run. This is because ZenML understands that nothing has changed between subsequent runs, so it re-uses the output of the last run (the outputs are persisted in the [artifact store](broken-reference/). This behavior is known as **caching**.

Prototyping is often a fast and iterative process that benefits a lot from caching. This makes caching a very powerful tool. Checkout this [ZenML Blogpost on Caching](https://blog.zenml.io/caching-ml-pipelines/) for more context on the benefits of caching and [ZenBytes lesson 1.2](https://github.com/zenml-io/zenbytes/blob/main/1-2\_Artifact\_Lineage.ipynb) for a detailed example on how to configure and visualize caching.

ZenML comes with caching enabled by default. Since ZenML automatically tracks and versions all inputs, outputs, and parameters of steps and pipelines, ZenML will not re-execute steps within the same pipeline on subsequent pipeline runs as long as there is no change in these three.

{% hint style="warning" %}
Currently, the caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching to `False` on steps that depend on external inputs or if the step should run regardless of caching.
{% endhint %}

### Configuring caching behavior of your pipelines

Although caching is desirable in many circumstances, one might want to disable it in certain instances. For example, if you are quickly prototyping with changing step definitions or you have an external API state change in your function that ZenML does not detect.

There are multiple ways to take control of when and where caching is used:

* [Configuring caching for the entire pipeline](create-your-first-ml-pipeline.md#disabling-caching-for-the-entire-pipeline): Do this if you want to configure caching for all steps of a pipeline.
* [Configuring caching for individual steps](create-your-first-ml-pipeline.md#disabling-caching-for-individual-steps): Do this to configure caching for individual steps. This is, e.g., useful to disable caching for steps that depend on external input.
* [Dynamically configuring caching for a pipeline run](create-your-first-ml-pipeline.md#dynamically-disabling-caching-for-a-pipeline-run): Do this if you want to change the caching behavior at runtime. This is, e.g., useful to force a complete rerun of a pipeline.

#### Configuring caching for the entire pipeline

On a pipeline level, the caching policy can be set as a parameter within the `@pipeline` decorator as shown below:

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

The setting above will disable caching for all steps in the pipeline, unless a step explicitly sets `enable_cache=True` (see below).

#### Configuring caching for individual steps

Caching can also be explicitly configured at a step level via a parameter of the `@step` decorator:

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
```

The code above turns caching off for this step only. This is very useful in practice since you might want to turn off caching for certain steps that take external input (like fetching data from an API or File IO) without affecting the overall pipeline caching behavior.

{% hint style="info" %}
You can get a graphical visualization of which steps were cached using the [ZenML Dashboard](broken-reference/).
{% endhint %}

#### Dynamically configuring caching for a pipeline run

Sometimes you want to have control over caching at runtime instead of defaulting to the hard-coded pipeline and step decorator settings. ZenML offers a way to override all caching settings at runtime:

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

The code above disables caching for all steps of your pipeline, no matter what you have configured in the `@step` or `@parameter` decorators.

### Code Example

The following example shows caching in action with the code example from the previous section.

For a more detailed example on how caching is used at ZenML and how it works under the hood, checkout [ZenBytes lesson 1.2](https://github.com/zenml-io/zenbytes/blob/main/1-2\_Artifact\_Lineage.ipynb)!

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

**Expected Output Run 1:**

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

**Expected Output Run 2:**

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

**Expected Output Run 3:**

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
