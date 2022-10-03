---
description: How to inspect a finished pipeline run
---

# Inspecting Pipeline Runs

Once a pipeline run has completed, we can access it using the post-execution
utilities.

Each pipeline can have multiple runs associated with it, and for each run there
might be several outputs for each step. Thus, to inspect a specific output, we
first need to access the respective pipeline, then fetch the respective run, 
and then choose the step output of that specific run.

The overall hierarchy looks like this:

```shell
pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

Let us investigate how to traverse this hierarchy level by level:

### Pipelines

ZenML keeps a collection of all created pipelines with at least one
run sorted by the time of their first run from oldest to newest.

You can either access this collection via the `get_pipelines()` method or query
a specific pipeline by name using `get_pipeline(pipeline=...)`:

```python
from zenml.post_execution import get_pipelines, get_pipeline

# get all pipelines from all stacks
pipelines = get_pipelines()

# now you can get pipelines by index
pipeline_with_latest_initial_run_time = pipelines[-1]

# or get one pipeline by name
pipeline_x = get_pipeline(pipeline="example_pipeline")

# or even use the pipeline class
pipeline_x = get_pipeline(pipeline=example_pipeline)
```

{% hint style="info" %}
Be careful when accessing pipelines by index. Even if you just ran a pipeline 
it might not be at index `-1`, due to the fact that the pipelines are sorted 
by time of *first* run. Instead, it is recommended to access the pipeline using 
the pipeline class, an instance of the class or even the name of the 
pipeline as a string: `get_pipeline(pipeline=...)`.
{% endhint %}

<details>
<summary>Using the CLI</summary>

You can also access your pipelines through the CLI by executing the following command on the terminal:

```
zenml pipeline list
```

</details>


### Runs

#### Getting runs from a fetched pipeline

Each pipeline can be executed many times. You can get a list of all runs using
the `runs` attribute of a pipeline.

```python
# get all runs of a pipeline chronologically ordered
runs = pipeline_x.runs 

# get the last run by index, runs are ordered by execution time in ascending order
last_run = runs[-1]

# or get a specific run by name
run = pipeline_x.get_run(run_name="my_run_name")
```

#### Getting runs from a pipeline instance:

Alternatively, you can also access the runs from the pipeline class/instance
itself:

```python
from zenml.pipelines import pipeline

# Definition of pipeline
@pipeline
def example_pipeline(...):
    ...

# Instantiation and execution of pipeline
pipe = example_pipeline(...)
pipe.run()

# get all runs of the defined pipeline chronologically ordered
runs = example_pipeline.get_runs()

# get all runs of the instantiated pipeline chronologically ordered
runs = pipe.get_runs()

# get the last run by index, runs are ordered by execution time in ascending order
last_run = runs[-1]

# or get a specific run by name
run = example_pipeline.get_run(run_name=...)
```

#### Directly getting a run

Finally, you can also access a run directly with the `get_run(run_name=...)`:

```python
run = get_run(run_name="my_run_name")
```

<details>
<summary>Using the CLI</summary>

You can also access your runs through the CLI by executing the following command on the terminal:

```
zenml pipeline runs list
zenml pipeline runs list -p <MY_PIPELINE_NAME_OR_ID>
```

</details>

### Runs Configuration

Each run has a collection of useful metadata which you can access:

**git_sha**
The Git commit SHA that the pipeline run was performed on. This will only be set 
if the pipeline code is in a git repository and there are no uncommitted files 
when running the pipeline.
```python
commit = run.git_sha
```

**status**
The status of a pipeline run can also be found here. There are four 
possible states: failed, completed, running, cached:
```python
status = run.status
```

**runtime_configuration**
Currently the runtime configuration contains information about the schedule that
was used for the run, the run_name and the path to the file containing the 
pipeline. 
```python
runtime_config = run.runtime_configuration
```


### Steps

Within a given pipeline run you can now further zoom in on individual steps
using the `steps` attribute or by querying a specific step using the
`get_step(step=...)` method.

```python
# get all steps of a pipeline for a given run
steps = run.steps

# get the step that was executed first
first_step = steps[0]

# or get a specific step by name
step = run.get_step(step="first_step")
```

{% hint style="warning" %}
The step `name` refers to the pipeline attribute and not the class name of the
steps that implement the step for a pipeline instance. 
{% endhint %}

```python
# Definition of pipeline
@pipeline
def example_pipeline(step_1, step_2):
    ...

# Initialize a new pipeline run
pipe = example_pipeline(step_1=first_step(), step_2=second_step())
pipe.run()

# Get the first step
pipe.get_runs()[-1].get_step(step="step_1")

# This won't work:
# pipe.get_runs()[-1].get_step(step="first_step")
```

{% hint style="info" %}
The steps are ordered by time of execution. Depending on the 
[orchestrator](../../mlops-stacks/orchestrators/orchestrators.md), steps can be 
run in parallel. Thus, accessing steps by index can be unreliable across 
different runs, and it is recommended to access steps by the step class,
an instance of the class or even the name of the step as a string: 
`get_step(step=...)` instead.
{% endhint %}

### Outputs

Finally, this is how you can inspect the output of a step:
- If there only is a single output, use the `output` attribute
- If there are multiple outputs, use the `outputs` attribute, which is a
dictionary that can be indexed using the name of an output:

```python
# The outputs of a step
# if there are multiple outputs they are accessible by name
output = step.outputs["output_name"]

# if there is only one output, use the `.output` property instead 
output = step.output 

# read the value into memory
output.read()  
```

{% hint style="info" %}
The names of the outputs can be found in the `Output` typing of your steps:

```python
from zenml.steps import step, Output


@step
def some_step() -> Output(output_name=int):
    ...
```
{% endhint %}

## Code Example

Putting it all together, this is how we can access the output of the last step
of our example pipeline from the previous sections:

```python
from zenml.post_execution import get_pipeline

pipeline = get_pipeline(pipeline="first_pipeline")
last_run = pipeline.runs[-1]
last_step = last_run.steps[-1]
model = last_step.output.read()
```

or alternatively:

```python
# Definition of pipeline
@pipeline
def example_pipeline(step_1, step_2):
    ...
# Initialize a new pipeline run
pipe = example_pipeline(step_1=first_step(), step_2=second_step())
pipe.run()

# Get the first step
step_1 = pipe.get_runs()[-1].get_step(step="step_1")
output = step_1.output.read()
```

# Older content (Page 2)

---
description: How to define pipelines and steps with functional and class-based APIs
---

In ZenML there are two different ways how you can define pipelines or steps.
What you have seen in the previous sections is the **Functional API**,
where steps and pipelines are defined as Python functions with a
`@step` or `@pipeline` decorator respectively.
This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the 
**Class-Based API** by creating Python classes that subclass ZenML's abstract
base classes `BaseStep` and `BasePipeline` directly.
Internally, both APIs will result in similar definitions, so it is
entirely up to you which API to use.

In the following, we will compare the two APIs using the code example from the
previous section on [Runtime Configuration](./runtime-configuration.md):

## Creating Steps

In order to create a step with the class-based API, you will need to create a
subclass of `zenml.steps.BaseStep` and implement its `entrypoint()` method to
perform the logic of the step.

{% tabs %}
{% tab title="Class-based API" %}
```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import BaseStep, BaseStepConfig


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


class SVCTrainerStep(BaseStep):
    def entrypoint(
        self,
        config: SVCTrainerStepConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> ClassifierMixin:
        """Train a sklearn SVC classifier."""
        model = SVC(gamma=config.gamma)
        model.fit(X_train, y_train)
        return model
```
{% endtab %}
{% tab title="Functional API" %}
```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step, BaseStepConfig


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


@step
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model
```
{% endtab %}
{% endtabs %}

## Creating Pipelines

Similarly, you can define a pipeline with the class-based API
by subclassing `zenml.pipelines.BasePipeline` and implementing its `connect()`
method:

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    def connect(self, step_1, step_2):
        X_train, X_test, y_train, y_test = step_1()
        step_2(X_train, y_train)


first_pipeline_instance = FirstPipeline(
    step_1=digits_data_loader(),
    step_2=SVCTrainerStep(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()

```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.pipelines import pipeline


@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)


first_pipeline_instance = first_pipeline(
    step_1=digits_data_loader(),
    step_2=SVCTrainerStep(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()
```
{% endtab %}
{% endtabs %}

As you saw in the example above, you can even mix and match the two APIs.
Choose whichever style feels most natural to you!

## Advanced Usage: Using decorators to give your steps superpowers

As you will learn later, ZenML has many [integrations](../../mlops-stacks/integrations.md)
that allow you to add functionality like automated experiment tracking to your steps.
Some of those integrations need to be initialized before they can be used, which
ZenML wraps using special `@enable_<INTEGRATION>` decorators.
Similar to the functional API, you can do this in the class-based API by 
adding a decorator to your `BaseStep` subclass:

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow


@enable_mlflow
class TFTrainer(BaseStep):
    def entrypoint(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
    ) -> tf.keras.Model:
        mlflow.tensorflow.autolog()
        ...
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.steps import step
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow


@enable_mlflow
@step
def tf_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    mlflow.tensorflow.autolog()
    ...
```
{% endtab %}
{% endtabs %}

Check out our [MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking), 
[Wandb](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking) and 
[whylogs](https://github.com/zenml-io/zenml/tree/main/examples/whylogs_data_profiling) 
examples for more information on how to use the specific decorators.
