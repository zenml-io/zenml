---
description: How to create ML pipelines in ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Steps & Pipelines

ZenML helps you standardize your ML workflows as ML **Pipelines** consisting of
decoupled, modular **Steps**. This enables you to write portable code that can be
moved from experimentation to production in seconds.

{% hint style="info" %}
If you are new to MLOps and would like to learn more about ML pipelines in 
general, checkout [ZenBytes](https://github.com/zenml-io/zenbytes), our lesson
series on practical MLOps, where we introduce ML pipelines in more detail in
[ZenBytes lesson 1.1](https://github.com/zenml-io/zenbytes/blob/main/1-1_Pipelines.ipynb).
{% endhint %}

## Step

Steps are the atomic components of a ZenML pipeline. Each step is defined by its
inputs, the logic it applies and its outputs. Here is a very basic example of
such a step, which uses a utility function to load the Digits dataset:

```python
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

from zenml.steps import Output, step


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
```

As this step has multiple outputs, we need to use the
`zenml.steps.step_output.Output` class to indicate the names of each output. 
These names can be used to directly access the outputs of steps after running
a pipeline, as we will see [in a later chapter](./fetching-pipelines.md).

Let's come up with a second step that consumes the output of our first step and
performs some sort of transformation on it. In this case, let's train a support
vector machine classifier on the training data using sklearn:

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step


@step
def svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model
```

Next, we will combine our two steps into our first ML pipeline.

{% hint style="info" %}
In case you want to run the step function outside the context of a ZenML 
pipeline, all you need to do is call the `.entrypoint()` method with the same
input signature. For example:

```python
svc_trainer.entrypoint(X_train=..., y_train=...)
```
{% endhint %}

<details>
<summary>Using the Class-based API</summary>

In ZenML there are two different ways how you can define pipelines or steps. What you have seen in this section so far is the Functional API, where steps and pipelines are defined as Python functions with a @step or @pipeline decorator respectively. This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the Class-Based API by creating Python classes that subclass ZenML's abstract base classes BaseStep and BasePipeline directly. Internally, both APIs will result in similar definitions, so it is entirely up to you which API to use.

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import BaseStep, BaseParameters


class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001


class SVCTrainerStep(BaseStep):
    def entrypoint(
        self,
        params SVCTrainerParams,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> ClassifierMixin:
        """Train a sklearn SVC classifier."""
        model = SVC(gamma=config.gamma)
        model.fit(X_train, y_train)
        return model
```
</details>

### Artifacts

The inputs and outputs of a step are *artifacts* that are automatically tracked
and stored by ZenML in the artifact store. Artifacts are produced by and
circulated among steps whenever your step returns an object or a value. If a
step returns only a single thing (value or object etc) there is no need to use
the `Output` class as shown above. 

If you want to dynamically update the hyperparameters of your pipeline, you can
use a subclass of `BaseParams` for that purpose (explained in full detail
[here](./parameters-and-caching.md)).

## Pipeline

Let us now define our first ML pipeline. This is agnostic of the implementation and can be
done by routing outputs through the steps within the pipeline. You can think of
this as a recipe for how we want data to flow through our steps.

```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)
```

<details>
<summary>Using the Class-based API</summary>

In ZenML there are two different ways how you can define pipelines or steps. What you have seen in this section so far is the Functional API, where steps and pipelines are defined as Python functions with a @step or @pipeline decorator respectively. This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the Class-Based API by creating Python classes that subclass ZenML's abstract base classes BaseStep and BasePipeline directly. Internally, both APIs will result in similar definitions, so it is entirely up to you which API to use.

```python
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    def connect(self, step_1, step_2):
        X_train, X_test, y_train, y_test = step_1()
        step_2(X_train, y_train)


first_pipeline_instance = FirstPipeline(
    step_1=digits_data_loader(),
    step_2=SVCTrainerStep(SVCTrainerParams(gamma=0.01)),
)
```
</details>


### Instantiate and run your Pipeline

With your pipeline recipe in hand you can now specify which concrete step
implementations to use when instantiating the pipeline:

```python
first_pipeline_instance = first_pipeline(
    step_1=digits_data_loader(),
    step_2=svc_trainer(),
)
```

You can then execute your pipeline instance with the `.run()` method:

```python
first_pipeline_instance.run()
```

You should see the following output in your terminal:

```shell
Registered new pipeline with name `first_pipeline`.
Creating run `first_pipeline-03_Oct_22-14_08_44_284312` for pipeline `first_pipeline` (Caching enabled)
Using stack `default` to run pipeline `first_pipeline`...
Step `digits_data_loader` has started.
Step `digits_data_loader` has finished in 0.121s.
Step `svc_trainer` has started.
Step `svc_trainer` has finished in 0.099s.
Pipeline run `first_pipeline-03_Oct_22-14_08_44_284312` has finished in 0.236s.
Pipeline visualization can be seen in the ZenML Dashboard. Run `zenml up` to see your pipeline!
```

We will dive deeper into how to inspect the finished run within the chapter on
[Accessing Pipeline Runs](./fetching-pipelines.md).

### Inspect your pipeline in the dashboard

Notice the last log, that indicates running a command to view the dashboard.
Check out the dashboard guide [in the next section](./dashboard.md) to inspect
your pipeline there.

### Give each pipeline run a name

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current
date and time as the name for the pipeline run. In order to change the name
for a run, pass `run_name` as a parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

{% hint style="warning" %}
Pipeline run names must be unique, so make sure to compute it dynamically if you
plan to run your pipeline multiple times.
{% endhint %}

### Unlisted runs

Once a pipeline has been executed, it is represented by a [`PipelineSpec`](https://apidocs.zenml.io) that uniquely identifies it. 
Therefore, you cannot edit a pipeline after it has been run once. In order to iterate quickly pipelines, there are three options:

- Pipeline runs can be created without being associated with a pipeline explicitly. These are called `unlisted` runs and can be created by passing 
the `unlisted` parameter when running a pipeline: `pipeline_instance.run(unlisted=True)`.
- Pipelines can be deleted and created again using `zenml pipeline delete <PIPELINE_ID_OR_NAME>`.
- Pipelines can be given [unique names](#give-each-pipeline-run-a-name) each time they are run to uniquely identify them.

We will dive into quickly iterating over pipelines [later in this section](iterating.md).

## Code Summary

<details>
<summary>Code Example for this Section</summary>

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.steps import Output, step
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


@step
def svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model


@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)


first_pipeline_instance = first_pipeline(
    step_1=digits_data_loader(),
    step_2=svc_trainer(),
)

first_pipeline_instance.run()
```

</details>
