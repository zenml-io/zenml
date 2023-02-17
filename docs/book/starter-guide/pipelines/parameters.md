---
description: Don't change the code, change the config!
---

# Configuring steps via parameters

Machine learning pipelines are rerun many times over throughout their development lifecycle.

In order to [iterate quickly](iteration.md), one must be able to quickly tweak pipeline runs by
changing various parameters for the steps that make up your pipeline.

{% hint style="info" %}
If you want to configure infrastructure related runtime settings of pipelines and stack components,
you'll want to [read the part of the Advanced Guide](../../advanced-guide/pipelines/settings.md)
where we dive into how to do this with `BaseSettings`.
{% endhint %}

## Parameterizing steps

You can parameterize a step by creating a subclass of the `BaseParameters`. When
an object like this is passed to a step, it is not handled like other 
[Artifacts](../../starter-guide/pipelines/pipelines.md#artifacts-link-steps-in-pipelines) within ZenML.
Instead, it gets passed into the step when the pipeline is instantiated.

```python
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step, BaseParameters


class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001


@step
def parameterized_svc_trainer(
    params: SVCTrainerParams,
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier with hyper-parameters."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=params.gamma) # Parameterized!
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model
```

The default value for the `gamma` parameter is set to `0.001` inside the
`SVCTrainerParams` object. However, when the pipeline is instantiated you can
override the default like this:

```python
first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=parameterized_svc_trainer(SVCTrainerParams(gamma=0.01)),
)

first_pipeline_instance.run()
```

By passing the `SVCTrainerParams` object to the instance of the pipeline, you
can amend and override the default values of the parameters. This is a very
powerful tool to quickly iterate over your pipeline.

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
when you [fetch pipeline runs](./fetching-pipelines.md), to compare various
runs, and of course all this information is also available in the ZenML
Dashboard.

<details>
<summary>How-To: Parameterization of a step</summary>
A practical example of how you might parameterize a step is shown below. We can start with a version of a step that has yet to be parameterized. You can see how arguments for `gamma`, `C` and `kernel` are passed in and are hard-coded in the step definition.

```python
@step
def parameterized_svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001, C=2.5, kernel='rbf')
    model.fit(X_train, y_train)
    return model
```

If you are in the early stages of prototyping, you might want to quickly iterate
over different values for `gamma`, `C` and `kernel`. Moreover, you might want to
store these as specific hyperparameters that are tracked alongside the rest of
the artifacts stored by ZenML. This is where `BaseParameters` comes in handy.

```python
class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001
    C: float = 1.0
    kernel: str = 'rbf'
```

Now, you can pass the `SVCTrainerParams` object to the step, and the values
inside the object will be used instead of the hard-coded values.

```python
@step
def parameterized_svc_trainer(
    params: SVCTrainerParams,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Simplified SVC classifier with np arrays."""
    model = SVC(gamma=params.gamma, C=params.C, kernel=params.kernel)
    model.fit(X_train, y_train)
    return model
```

Finally, you can pass the `SVCTrainerParams` object to the instance of the
pipeline, and override the default values of the parameters.

```python
first_pipeline_instance = first_pipeline(
    step_1=data_loader(),
    step_2=parameterized_svc_trainer(SVCTrainerParams(gamma=0.01, C=2.5, kernel='linear')),
)
```

Parameterizing steps in ML pipelines is a crucial aspect of efficient and
effective machine learning. By separating the configuration from the code, data
scientists and machine learning engineers have greater control over the behavior
of each step in the pipeline. This makes it easier to tune and optimize each
step, as well as to reuse the code in different pipelines or experiments.
Additionally, parameterization helps to make the pipelines more robust and
reproducible, as the configuration can be stored and versioned alongside the
code. Ultimately, parameterizing steps in ML pipelines can lead to improved
model performance, reduced development time, and increased collaboration among
team members.
</details>
