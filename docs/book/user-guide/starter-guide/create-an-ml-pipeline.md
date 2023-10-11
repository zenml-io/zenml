---
description: Learning how to configure pipelines and their steps.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Create an ML pipeline

In this section, we build out the first ML pipeline. For this, let's get the imports out of the way first:

```python
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml import pipeline, step
from zenml.steps import Output
```

Make sure to install the requirements as well:

```bash
pip install matplotlib
zenml integration install sklearn
```

In this case, ZenML has an integration with `sklearn` so you can use the ZenML CLI to install the right version directly.

#### Steps with multiple outputs

Sometimes a step will have multiple outputs. In order to give each output a unique name, use the `Output()` annotation. Here we load an open-source dataset and split it into a train and a test dataset.

```python
@step
def training_data_loader() -> Output(
    X_train=pd.DataFrame,
    X_test=pd.DataFrame,
    y_train=pd.Series,
    y_test=pd.Series,
):
    """Load the iris dataset as tuple of Pandas DataFrame / Series."""
    iris = load_iris(as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, shuffle=True, random_state=42
    )
    return X_train, X_test, y_train, y_test

```

#### Parametrizing a step

Here we are creating a training step for a support vector machine classifier with `sklearn`. As we might want to adjust the hyperparameter `gamma` later on, we define it as an input value to the step as well.

```python
@step(enable_cache=False)
def svc_trainer(
        X_train: pd.DataFrame,
        y_train: pd.Series,
        gamma: float = 0.001,
) -> Output(trained_model=ClassifierMixin, training_acc=float):
    """Train a sklearn SVC classifier."""

    model = SVC(gamma=gamma)
    model.fit(X_train.to_numpy(), y_train.to_numpy())

    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")

    return model, train_acc
```

{% hint style="info" %}
If you want to run the step function outside the context of a ZenML pipeline, all you need to do is call the `.entrypoint()` method with the same input signature. For example:

```python
svc_trainer.entrypoint(X_train=..., y_train=...)
```
{% endhint %}

Next, we will combine our two steps into a pipeline and run it. As you can see, the parameter gamma is configurable as a pipeline input.

```python
@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)


if __name__ == "__main__":
    first_pipeline(gamma=0.0015)
```

{% hint style="info" %}
Best Practice: Always nest the actual execution of the pipeline inside an `if __name__ == "__main__"` condition. This ensures that loading the pipeline from elsewhere does not also run it.

```python
if __name__ == "__main__":
    first_pipeline()
```
{% endhint %}

Running `python main.py` should look somewhat like this in the terminal:

<pre class="language-sh" data-line-numbers><code class="lang-sh"><strong>Registered new pipeline with name `first_pipeline`.
</strong>.
.
.
Pipeline run `first_pipeline-2023_04_29-09_19_54_273710` has finished in 0.236s.
</code></pre>

In the dashboard, you should now be able to see this new run, along with its runtime configuration and a visualization of the training data.

<figure><img src="../../.gitbook/assets/RunWithVisualization.png" alt=""><figcaption><p>Run created by the code in this section along with a visualization of the ground-truth distribution.</p></figcaption></figure>

#### Give each pipeline run a name

In the output logs of a pipeline run you will see the name of the run:

```bash
Pipeline run first_pipeline-2023_05_24-12_41_04_576473 has finished in 3.742s.
```

This name is automatically generated based on the current date and time. To change the name for a run, pass `run_name` as a parameter to the `with_options()` method:

```python
first_pipeline = first_pipeline.with_options(
    run_name="custom_pipeline_run_name"
)
first_pipeline()
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or run them on a schedule, make sure to either compute the run name dynamically or include one of the following placeholders that ZenML will replace:

* `{{date}}` will resolve to the current date, e.g. `2023_02_19`
* `{{time}}` will resolve to the current time, e.g. `11_07_09_326492`

```python
first_pipeline = first_pipeline.with_options(
    run_name="custom_pipeline_run_name_{{date}}_{{time}}"
)
first_pipeline()
```

## Code Example

The following example shows caching in action with the code example from the previous section.

<details>

<summary>Code Example of this Section</summary>

```python
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml import pipeline, step
from zenml.steps import Output


@step
def training_data_loader() -> Output(
    X_train=pd.DataFrame,
    X_test=pd.DataFrame,
    y_train=pd.Series,
    y_test=pd.Series,
):
    """Load the iris dataset as tuple of Pandas DataFrame / Series."""
    iris = load_iris(as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, shuffle=True, random_state=42
    )
    return X_train, X_test, y_train, y_test


@step(enable_cache=False)
def svc_trainer(
        X_train: pd.DataFrame,
        y_train: pd.Series,
        gamma: float = 0.001,
) -> Output(trained_model=ClassifierMixin, training_acc=float):
    """Train a sklearn SVC classifier and log to MLflow."""
    model = SVC(gamma=gamma)
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")
    return model, train_acc


@pipeline
def first_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)


if __name__ == "__main__":
    first_pipeline()

    # Step one will use cache, step two will rerun due to the decorator config
    first_pipeline(gamma=0.0001)
```

</details>
