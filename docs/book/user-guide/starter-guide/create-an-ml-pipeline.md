---
description: Start with the basics of steps and pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Create an ML pipeline

In the quest for production-ready ML models, workflows can quickly become complex. Decoupling and standardizing stages such as data ingestion, preprocessing, and model evaluation allows for more manageable, reusable, and scalable processes. ZenML pipelines facilitate this by enabling each stage—represented as **Steps**—to be modularly developed and then integrated smoothly into an end-to-end **Pipeline**.

Leveraging ZenML, you can create and manage robust, scalable machine learning (ML) pipelines. Whether for data preparation, model training, or deploying predictions, ZenML standardizes and streamlines the process, ensuring reproducibility and efficiency.

<figure><img src="../../.gitbook/assets/pipeline_showcase.png" alt=""><figcaption><p>ZenML pipelines are simple Python code</p></figcaption></figure>

{% hint style="info" %}
Before starting this guide, make sure you have [installed ZenML](../../getting-started/installation.md):

```shell
pip install "zenml[server]"
zenml login --local  # Will launch the dashboard locally
```
{% endhint %}

## Start with a simple ML pipeline

Let's jump into an example that demonstrates how a simple pipeline can be set up in ZenML, featuring actual ML components to give you a better sense of its application.

```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    """Simulates loading of training data and labels."""

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: dict) -> None:
    """
    A mock 'training' process that also demonstrates using the input data.
    In a real-world scenario, this would be replaced with actual model fitting logic.
    """
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")

@pipeline
def simple_ml_pipeline():
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    train_model(dataset)

if __name__ == "__main__":
    run = simple_ml_pipeline()
    # You can now use the `run` object to see steps, outputs, etc.
```

{% hint style="info" %}
* **`@step`** is a decorator that converts its function into a step that can be used within a pipeline
* **`@pipeline`** defines a function as a pipeline and within this function, the steps are called and their outputs link them together.
{% endhint %}

Copy this code into a new file and name it `run.py`. Then run it with your command line:

{% code overflow="wrap" %}
```bash
$ python run.py

Initiating a new run for the pipeline: simple_ml_pipeline.
Executing a new run.
Using user: hamza@zenml.io
Using stack: default
  orchestrator: default
  artifact_store: default
Step load_data has started.
Step load_data has finished in 0.385s.
Step train_model has started.
Trained model using 3 data points. Feature sum is 21, label sum is 1
Step train_model has finished in 0.265s.
Run simple_ml_pipeline-2023_11_23-10_51_59_657489 has finished in 1.612s.
Pipeline visualization can be seen in the ZenML Dashboard. Run zenml login --local to see your pipeline!
```
{% endcode %}

### Explore the dashboard

Once the pipeline has finished its execution, use the `zenml login --local` command to view the results in the ZenML Dashboard. Using that command will open up the browser automatically.

<figure><img src="../../.gitbook/assets/landingpage.png" alt=""><figcaption><p>Landing Page of the Dashboard</p></figcaption></figure>

Usually, the dashboard is accessible at [http://127.0.0.1:8237/](http://127.0.0.1:8237/). Log in with the default username **"default"** (password not required) and see your recently run pipeline. Browse through the pipeline components, such as the execution history and artifacts produced by your steps. Use the DAG visualization to understand the flow of data and to ensure all steps are completed successfully.

<figure><img src="../../.gitbook/assets/DAGofRun.png" alt=""><figcaption><p>Diagram view of the run, with the runtime attributes of step 2.</p></figcaption></figure>

For further insights, explore the logging and artifact information associated with each step, which can reveal details about the data and intermediate results.

If you have closed the browser tab with the ZenML dashboard, you can always reopen it by running `zenml show` in your terminal.

## Understanding steps and artifacts

When you ran the pipeline, each individual function that ran is shown in the DAG visualization as a `step` and is marked with the function name. Steps are connected with `artifacts`, which are simply the objects that are returned by these functions and input into downstream functions. This simple logic lets us break down our entire machine learning code into a sequence of tasks that pass data between each other.

The artifacts produced by your steps are automatically stored and versioned by ZenML. The code that produced these artifacts is also automatically tracked. The parameters and all other configuration is also automatically captured.

So you can see, by simply structuring your code within some functions and adding some decorators, we are one step closer to having a more tracked and reproducible codebase!

## Expanding to a Full Machine Learning Workflow

With the fundamentals in hand, let’s escalate our simple pipeline to a complete ML workflow. For this task, we will use the well-known Iris dataset to train a Support Vector Classifier (SVC).

Let's start with the imports.

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
The `zenml integration install sklearn` command is simply doing a `pip install` of `sklearn` behind the scenes. If something goes wrong, one can always use `zenml integration requirements sklearn` to see which requirements are compatible and install using pip (or any other tool) directly. (If no specific requirements are mentioned for an integration then this means we support using all possible versions of that integration/package.)
{% endhint %}

### Define a data loader with multiple outputs

A typical start of an ML pipeline is usually loading data from some source. This step will sometimes have multiple outputs. To define such a step, use a `Tuple` type annotation. Additionally, you can use the `Annotated` annotation to assign [custom output names](manage-artifacts.md#giving-names-to-your-artifacts). Here we load an open-source dataset and split it into a train and a test dataset.

```python
import logging

@step
def training_data_loader() -> Tuple[
    # Notice we use a Tuple and Annotated to return 
    # multiple named outputs
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
@step
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
If you want to run just a single step on your ZenML stack, all you need to do is call the step function outside of a ZenML pipeline. For example:

```python
model, train_acc = svc_trainer(X_train=..., y_train=...)
```
{% endhint %}

Next, we will combine our two steps into a pipeline and run it. As you can see, the parameter gamma is configurable as a pipeline input as well.

```python
@pipeline
def training_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)


if __name__ == "__main__":
    training_pipeline(gamma=0.0015)
```

{% hint style="info" %}
Best Practice: Always nest the actual execution of the pipeline inside an `if __name__ == "__main__"` condition. This ensures that loading the pipeline from elsewhere does not also run it.

```python
if __name__ == "__main__":
    training_pipeline()
```
{% endhint %}

Running `python run.py` should look somewhat like this in the terminal:

<pre class="language-sh" data-line-numbers><code class="lang-sh"><strong>Registered new pipeline with name `training_pipeline`.
</strong>.
.
.
Pipeline run `training_pipeline-2023_04_29-09_19_54_273710` has finished in 0.236s.
</code></pre>

In the dashboard, you should now be able to see this new run, along with its runtime configuration and a visualization of the training data.

<figure><img src="../../.gitbook/assets/RunWithVisualization.png" alt=""><figcaption><p>Run created by the code in this section along with a visualization of the ground-truth distribution.</p></figcaption></figure>

### Configure with a YAML file

Instead of configuring your pipeline runs in code, you can also do so from a YAML file. This is best when we do not want to make unnecessary changes to the code; in production this is usually the case.

To do this, simply reference the file like this:

```python
# Configure the pipeline
training_pipeline = training_pipeline.with_options(
    config_path='/local/path/to/config.yaml'
)
# Run the pipeline
training_pipeline()
```

The reference to a local file will change depending on where you are executing the pipeline and code from, so please bear this in mind. It is best practice to put all config files in a configs directory at the root of your repository and check them into git history.

A simple version of such a YAML file could be:

```yaml
parameters:
    gamma: 0.01
```

Please note that this would take precedence over any parameters passed in the code.

If you are unsure how to format this config file, you can generate a template config file from a pipeline.

```python
training_pipeline.write_run_configuration_template(path='/local/path/to/config.yaml')
```

Check out [this section](../../how-to/pipeline-development/use-configuration-files/README.md) for advanced configuration options.

## Full Code Example

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


@step
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
def training_pipeline(gamma: float = 0.002):
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)


if __name__ == "__main__":
    training_pipeline()
```

</details>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
