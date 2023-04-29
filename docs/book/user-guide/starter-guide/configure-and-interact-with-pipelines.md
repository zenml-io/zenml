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
    X_train: np.ndarray,
    y_train: np.ndarray,
    gamma: float = 0.001,
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
    step_2(gamma=gamma, X_train=X_train, y_train=y_train)
    
first_pipeline(gamma=0.0015)
```

Running it should look somewhat like this in the terminal.

<pre class="language-sh" data-line-numbers><code class="lang-sh">$python main.py
<strong>Registered new pipeline with name `first_pipeline`.
</strong>.
.
.
Pipeline run `first_pipeline-2023_04_29-09_19_54_273710` has finished in 0.236s.
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

In the output logs of a pipeline run you will see the name of the run:

```bash
Pipeline run `first_pipeline-2023_04_29-09_19_54_273710` has finished in 0.236s.
```

This name is automatically generated based on the current date and time. In order to change the name for a run, pass `run_name` as a parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or run them on a schedule, make sure to either compute the run name dynamically or include one of the following placeholders that will be replaced by ZenML:

* `{{date}}` will resolve to the current date, e.g. `2023_02_19`
* `{{time}}` will resolve to the current time, e.g. `11_07_09_326492`

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name_{{date}}_{{time}}")
```

### Caching in ZenML

You might have noticed at this point that rerunning the pipeline a second time gives you the following logs:

```bash
Step step_1 has started.
Using cached version of step_1.
Step step_2 has started.
Using cached version of step_2.
```

This is because ZenML understands that nothing has changed between subsequent runs, so it re-uses the output of the last run (the outputs are persisted in the [artifact store](broken-reference/). This behavior is known as **caching**.

ZenML comes with caching enabled by default. Since ZenML automatically tracks and versions all inputs, outputs, and parameters of steps and pipelines, ZenML will not re-execute steps within the same pipeline on subsequent pipeline runs as long as there is no change in these three.

{% hint style="warning" %}
Currently, the caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching to `False` on steps that depend on external inputs or if the step should run regardless of caching.
{% endhint %}

### Configuring caching behavior of your pipelines

Although caching is desirable in many circumstances, one might want to disable it in certain instances. For example, if you are quickly prototyping with changing step definitions or you have an external API state change in your function that ZenML does not detect.

There are multiple ways to take control of when and where caching is used:

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

<details>

<summary>Code Example of this Section</summary>

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

# The pipeline is executed for the first time, so all steps are run.
first_pipeline()

# Step one will use cache, step two will rerun due to the decorator config
first_pipeline()

# Explicitely set caching to false
first_pipeline.with_option(enable_cache=False)()  # Explicitely disable the cache

```

**Expected Output Run 1:**

{% code overflow="wrap" %}
```bash
Registered pipeline first_pipeline (version 1).
Running pipeline first_pipeline on stack default (caching enabled)
Step digits_data_loader has started.
Step digits_data_loader has finished in 0.721s.
Step svc_trainer has started.
Step svc_trainer has finished in 0.172s.
Pipeline run first_pipeline-2023_04_29-10_13_02_708462 has finished in 1.717s.
Dashboard URL: http://127.0.0.1:8237/workspaces/default/pipelines/43ddd41b-aedc-4893-856d-f51eaf9a8699/runs

```
{% endcode %}

**Expected Output Run 2:**

{% code overflow="wrap" %}
```bash
Reusing registered pipeline first_pipeline (version: 1).
Running pipeline first_pipeline on stack default (caching enabled)
Step digits_data_loader has started.
Using cached version of digits_data_loader.
Step svc_trainer has started.
Using cached version of svc_trainer.
Pipeline run first_pipeline-2023_04_29-10_13_05_400797 has finished in 0.609s.
Dashboard URL: http://127.0.0.1:8237/workspaces/default/pipelines/43ddd41b-aedc-4893-856d-f51eaf9a8699/runs
```
{% endcode %}

**Expected Output Run 3:**

{% code overflow="wrap" %}
```bash
Reusing registered pipeline first_pipeline (version: 1).
Running pipeline first_pipeline on stack default (caching disabled)
Step digits_data_loader has started.
Step digits_data_loader has finished in 0.721s.
Step svc_trainer has started.
Step svc_trainer has finished in 0.226s.
Pipeline run first_pipeline-2023_04_29-10_13_06_840942 has finished in 0.942s.
Dashboard URL: http://127.0.0.1:8237/workspaces/default/pipelines/43ddd41b-aedc-4893-856d-f51eaf9a8699/runs
```
{% endcode %}

</details>
