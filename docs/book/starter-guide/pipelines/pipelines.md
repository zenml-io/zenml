---
description: How to create ML pipelines in ZenML
---

# Start your MLOps journey with ZenML

## 🥼 Set up your template

Hey there! Welcome the world of MLOps, presented through the window of ZenML!
In this guide, you will learn about how to use the ZenML open-source MLOps framework
to guide your machine learning models to production. Let's begin with setting up.
Make sure you have Python 3.7 or above installed, and in a fresh
[virtualenv](https://virtualenv.pypa.io/en/latest/) do:

```shell
# Install ZenML with the right extras
pip install "zenml[server,templates]"

# Create a new directory
mkdir mlops_starter
cd mlops_starter

# Initialize a ZenML repository
zenml example pull starter_guide  # soon to be replaced with `zenml init --starter`
cd starter_guide

# If you have VS Code, now is the time to open it!
code .
```

Pro tip: Open up the `starter_guide` in your favorite IDE to inspect the code as you
go through this guide.

Now, you are ready to begin. Let's dive into your local code!

## 🚶‍♀️First Steps

ZenML helps you standardize your ML workflows as ML **Pipelines** consisting of
decoupled, modular **Steps**. This enables you to write portable code that can be
moved from experimentation to production in seconds.

{% hint style="info" %}
If you are new to MLOps and would like to learn more about ML pipelines in 
general, checkout [ZenBytes](https://github.com/zenml-io/zenbytes), our lesson
series on practical MLOps, where we introduce ML pipelines in more detail in
[ZenBytes lesson 1.1](https://github.com/zenml-io/zenbytes/blob/main/1-1_Pipelines.ipynb).
{% endhint %}

Steps are the atomic components of a ZenML pipeline. Each step is defined by its
inputs, the logic it applies, and its outputs. Steps are simple Python functions
with some annotations. You can see your first steps in the
`steps/data_loaders.py` file in the starter template, specifically the last one:

```python
import pandas as pd
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split

from zenml.steps import Output, step

@step
def simple_data_splitter() -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame):
    # Load the wine dataset
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set
```

As this step has multiple outputs, we need to use the
`zenml.steps.step_output.Output` class to indicate the names of each output. 
These names can be used to directly access the outputs of steps after running
a pipeline, as we will see [in a later chapter](./fetching-pipelines.md).
If a step returns only a single thing (value or object etc) there is no need to use
the `Output` class as shown above. 

Let's come up with a second step that consumes the output of our first step and
performs some sort of transformation on it. In this case, let's train a support
vector machine classifier on the training data and score it with the test set.
You can see the step in the file `steps/model_trainers.py`. 

```python
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step


@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model
```

As you can see, you can put your steps in one or multiple files, but the more
you logically seperate them in your directory structure the better. In most cases,
it is best to put all your steps in a seperate module called `steps`, as is shown
in the starter template!

{% hint style="info" %}
In case you want to run the step function outside the context of a ZenML 
pipeline, all you need to do is call the `.entrypoint()` method with the same
input signature. For example:

```python
simple_svc_trainer.entrypoint(train_set=..., test_set=...)
```
{% endhint %}

<details>
<summary>Using the Class-based API</summary>

In ZenML there are two different ways how you can define pipelines or steps. What you have seen in this section so far is the Functional API, where steps and pipelines are defined as Python functions with a @step or @pipeline decorator respectively. This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the Class-Based API by creating Python classes that subclass ZenML's abstract base classes BaseStep and BasePipeline directly. Internally, both APIs will result in similar definitions, so it is entirely up to you which API to use.

```python
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import BaseStep, BaseParameters


class SVCTrainerStep(BaseStep):
    def entrypoint(
        self,
        train_set: pd.DataFrame,
        test_set: pd.DataFrame,
    ) -> ClassifierMixin:
        """Train a sklearn SVC classifier."""
        X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
        X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
        model = SVC(gamma=0.001)
        model.fit(X_train, y_train)
        test_acc = model.score(X_test, y_test)
        print(f"Test accuracy: {test_acc}")
        return model
```
</details>

## 🔌 Connecting steps with Pipelines

Let us now define our first ML pipeline. This is agnostic of the implementation and can be
done by routing outputs through the steps within the pipeline. You can think of
this as a recipe for how we want data to flow through our steps.

```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(step_1, step_2):
    train_set, test_set = step_1()
    step_2(train_set, test_set)
```

### 🏃 Instantiate and run your Pipeline

With your pipeline recipe in hand you can now specify which concrete step
implementations to use when instantiating the pipeline:

```python
first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=simple_svc_trainer(),
)
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
    step_1=simple_data_splitter(),
    step_2=SVCTrainerStep(),
)
```
</details>

You can then execute your pipeline instance with the `.run()` method:

```python
first_pipeline_instance.run()
```

If you're not in the mood of copy-pasting the above into another file, we got you covered! Just
use the starter template and run:

```
python run.py --simple
```

You should see the following output in your terminal:

```shell
Registered new pipeline with name `first_pipeline`.
Creating run `first_pipeline-03_Oct_22-14_08_44_284312` for pipeline `first_pipeline` (Caching enabled)
Using stack `default` to run pipeline `first_pipeline`...
Step `simple_data_splitter` has started.
Step `simple_data_splitter` has finished in 0.121s.
Step `simple_svc_trainer` has started.
Step `simple_svc_trainer` has finished in 0.099s.
Pipeline run `first_pipeline-03_Oct_22-14_08_44_284312` has finished in 0.236s.
Pipeline visualization can be seen in the ZenML Dashboard. Run `zenml up` to see your pipeline!
```

We will dive deeper into how to inspect the finished run within the chapter on
[Accessing Pipeline Runs](./fetching-pipelines.md).

### 👀 Inspect your pipeline in the dashboard

Notice the last log, that indicates running a command to view the dashboard.
Check out the dashboard guide [in another section](./dashboard.md) to inspect
your pipeline there.

```
zenml up
```

### 💯 Give each pipeline run a (dynamic) name

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current
date and time as the name for the pipeline run. In order to change the name
for a run, pass `run_name` as a parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or
run them on a schedule, make sure to either compute the run name dynamically or include
one of the following placeholders that will be replaced by ZenML:
- `{{date}}` will resolve to the current date, e.g. `2023_02_19`
- `{{time}}` will resolve to the current time, e.g. `11_07_09_326492`

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name_{{date}}_{{time}}")
```

### 🎽 Unlisted runs

Once a pipeline has been executed, it is represented by a [`PipelineSpec`](https://apidocs.zenml.io) that uniquely identifies it. 
Therefore, you cannot edit a pipeline after it has been run once. In order to iterate quickly pipelines, there are three options:

- Pipeline runs can be created without being associated with a pipeline explicitly. These are called `unlisted` runs and can be created by passing 
the `unlisted` parameter when running a pipeline: `pipeline_instance.run(unlisted=True)`.
- Pipelines can be deleted and created again using `zenml pipeline delete <PIPELINE_ID_OR_NAME>`.
- Pipelines can be given [unique names](#give-each-pipeline-run-a-name) each time they are run to uniquely identify them.

We will dive into quickly iterating over pipelines [later in this section](iteration.md.md).


## 🦖 Artifacts link steps in pipelines

The inputs and outputs of a step are *artifacts* that are automatically tracked
and stored by ZenML in the artifact store. Artifacts are produced by and
circulated among steps whenever your step returns an object or a value. 

Artifacts can be fetched post-run by using the simple client API:

```python
from zenml.post_execution import get_pipelines

# get all pipelines from all stacks
pipelines = get_pipelines()

# now you can get pipelines by index
pipeline_with_latest_initial_run_time = pipelines[-1]

# get the last run by index, runs are ordered by execution time in ascending order
last_run = pipeline_with_latest_initial_run_time.runs[-1]

# get the step that was executed first
first_step = steps[0]
git status

# if there are multiple outputs they are accessible by name
output = step.outputs["train_set"]

# read the value into memory
train_set = output.read()  
```

You will learn more about this in a [later chapter](./fetching-pipelines.md).

## Code Summary

The entire code of this section can be found in the `steps` and `pipelines` directory of the
starter template.

<details>
<summary>Code Example for this Section</summary>

```python
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.steps import Output, step
from zenml.pipelines import pipeline


@step
def simple_data_splitter() -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame):
    # Load the wine dataset
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set


@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model


@pipeline
def first_pipeline(step_1, step_2):
    train_set, test_set = step_1()
    step_2(train_set, test_set)


first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=simple_svc_trainer(),
)

first_pipeline_instance.run()
```

</details>
