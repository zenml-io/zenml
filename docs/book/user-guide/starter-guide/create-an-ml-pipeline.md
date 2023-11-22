---
description: Start with the basics of steps and pipelines.
---

# Developing ML pipelines

ZenML helps you standardize your ML workflows as **Pipelines** consisting of decoupled, modular **Steps**. This enables you to write portable code that can be moved from experimentation to production in seconds.

## Start with a simple pipeline

The simplest ZenML pipeline could look like this:

```python
from zenml import pipeline, step


@step
def step_1() -> str:
    """Returns the `world` string."""
    return "world"


@step(enable_cache=False)
def step_2(input_one: str, input_two: str) -> None:
    """Combines the two strings at its input and prints them."""
    combined_str = f"{input_one} {input_two}"
    print(combined_str)


@pipeline
def my_pipeline():
    output_step_one = step_1()
    step_2(input_one="hello", input_two=output_step_one)


if __name__ == "__main__":
    my_pipeline()
```

{% hint style="info" %}
* **`@step`** is a decorator that converts its function into a step that can be used within a pipeline
* **`@pipeline`** defines a function as a pipeline and within this function, the steps are called and their outputs are routed
{% endhint %}

Copy this code into a file `run.py` and run it.

{% code overflow="wrap" %}
```bash
$ python run.py

Registered pipeline my_pipeline (version 1).
Running pipeline my_pipeline on stack default (caching enabled)
Step step_1 has started.
Step step_1 has finished in 0.121s.
Step step_2 has started.
hello world
Step step_2 has finished in 0.046s.
Pipeline run my_pipeline-... has finished in 0.676s.
Pipeline visualization can be seen in the ZenML Dashboard. Run zenml up to see your pipeline!
```
{% endcode %}

In the output, there's a line with something like this.

{% code overflow="wrap" %}
```bash
Pipeline visualization can be seen in the ZenML Dashboard. Run zenml up to see your pipeline!
```
{% endcode %}

## Explore the dashboard

Run `zenml up` in the environment where you have ZenML installed.

After a few seconds, your browser should open the ZenML Dashboard for you at [http://127.0.0.1:8237/](http://127.0.0.1:8237/)

The default user account is **Username**: _**default**_ with **no** **password**.

<figure><img src="../../.gitbook/assets/landingpage.png" alt=""><figcaption><p>Landing Page of the Dashboard</p></figcaption></figure>

As you can see, the dashboard shows you that there is 1 pipeline and 1 pipeline run. (feel free to ignore the stack and components for the time being) and continue to the run you just executed.

<figure><img src="../../.gitbook/assets/DAGofRun.png" alt=""><figcaption><p>Diagram view of the run, with the runtime attributes of step 2.</p></figcaption></figure>

If you navigate to the run that you just executed, you will see a diagram view of the pipeline run, including a visualization of the data that is passed between the steps. Feel free to explore the Run, its steps, and its artifacts.

If you have closed the browser tab with the ZenML dashboard, you can always reopen it by running `zenml show` in your terminal.

## Develop a ML pipeline

In this section, we build out the first ML pipeline. For this, let's get the imports out of the way first:

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Tuple
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml import pipeline, step
```

Make sure to install the requirements as well:

```bash
pip install matplotlib
zenml integration install sklearn -y
```

In this case, ZenML has an integration with `sklearn` so you can use the ZenML CLI to install the right version directly.

{% hint style="info" %}
The `zenml integration install sklearn` command is simply doing a `pip install sklearn<1.3` behind the scenes. If something goes wrong, one can always use `zenml integration requirements sklearn` to see which requirements are compatible and install using pip (or any other tool) directly.
{% endhint %}

### Define a data loader with multiple outputs

A typical start of a ML pipeline is usually loading data from some source. This step will sometimes have multiple outputs. To define such a step, use a `Tuple` type annotation.
Additionally, you can use the `Annotated` annotation to assign
[custom output names](../advanced-guide/pipelining-features/configure-steps-pipelines.md#step-output-names).
Here we load an open-source dataset and split it into a train and a test dataset.

```python
import logging

@step
def training_data_loader() -> Tuple[
    Annotated[pd.DataFrame, "X_train"],
    Annotated[pd.DataFrame, "X_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"],
]:
    """Load the iris dataset as a tuple of Pandas DataFrame / Series."""
    logging.info("Loading iris...")
    iris = load_iris(as_frame=True)
    logging.info("Splitting train and test...")
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, shuffle=True, random_state=42
    )
    return X_train, X_test, y_train, y_test

```

{% hint style="info" %}
ZenML records the root python logging handler's output into the artifact store as a side-effect of running a step. Therefore, when writing steps, use the `logging` module to record logs, to ensure that these logs then show up in the ZenML dashboard.
{% endhint %}

### Create a parameterized training step

Here we are creating a training step for a support vector machine classifier with `sklearn`. As we might want to adjust the hyperparameter `gamma` later on, we define it as an input value to the step as well.

```python
@step(enable_cache=False)
def svc_trainer(
        X_train: pd.DataFrame,
        y_train: pd.Series,
        gamma: float = 0.001,
) -> Tuple[
    Annotated[ClassifierMixin, "trained_model"],
    Annotated[float, "training_acc"],
]:
    """Train a sklearn SVC classifier."""

    model = SVC(gamma=gamma)
    model.fit(X_train.to_numpy(), y_train.to_numpy())

    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")

    return model, train_acc
```

{% hint style="info" %}
If you want to run the step function outside the context of a ZenML pipeline, all you need to do is call the step function outside of a ZenML pipeline. For example:

```python
svc_trainer(X_train=..., y_train=...)
```
{% endhint %}

Next, we will combine our two steps into a pipeline and run it. As you can see, the parameter gamma is configurable as a pipeline input as well.

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

Running `python run.py` should look somewhat like this in the terminal:

<pre class="language-sh" data-line-numbers><code class="lang-sh"><strong>Registered new pipeline with name `first_pipeline`.
</strong>.
.
.
Pipeline run `first_pipeline-2023_04_29-09_19_54_273710` has finished in 0.236s.
</code></pre>

In the dashboard, you should now be able to see this new run, along with its runtime configuration and a visualization of the training data.

<figure><img src="../../.gitbook/assets/RunWithVisualization.png" alt=""><figcaption><p>Run created by the code in this section along with a visualization of the ground-truth distribution.</p></figcaption></figure>

### Configure with a yaml file

Instead of configuring your pipeline runs in code, you can also do so from a YAML file. This is best when we do not want to make unnecessary changes to the code (in production this is usually the case).

To do this, simply reference the file like this:

```python
first_pipeline = first_pipeline.with_options(
    config_path='/local/path/to/config.yaml'
)
first_pipeline()
```

A simple version of such a YAML file could be:

```yaml
steps:
  svc_trainer:
    enable_cache: False
    parameters:
      gamma: 0.01
```

Please note that this would take precendence over any parameters passed in code.

If you are unsure how to format this config file, you can generate a template
config file from a pipeline.

```python
first_pipeline.write_run_configuration_template(path='/local/path/to/config.yaml')
```

Check out [this page](../advanced-guide/pipelining-features/configure-steps-pipelines.md#method-3-configuring-with-yaml)
for more details.


### Give each pipeline run a name

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

### Full Code Example

This section combines all the code from this section into one simple script that you can use to run easily:

<details>

<summary>Code Example of this Section</summary>

```python
from typing_extensions import Tuple, Annotated
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml import pipeline, step


@step
def training_data_loader() -> Tuple[
    Annotated[pd.DataFrame, "X_train"],
    Annotated[pd.DataFrame, "X_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"],
]:
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
) -> Tuple[
    Annotated[ClassifierMixin, "trained_model"],
    Annotated[float, "training_acc"],
]:
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

    # Step one will use cache, step two will rerun due to caching
    # being disabled on the @step decorator. Even if caching was
    # enabled though, ZenML would detect a different value for the
    # `gamma` input of the second step and disable caching
    first_pipeline(gamma=0.0001)
```

</details>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
