---
description: Iteration is native to ZenML with fast caching.
---

# Quickly iterating in ZenML

ZenML tries its best to get out of the way as you run your ML experiments. For this, it has
built in pipeline versioning and caching support to help your local work be as fast as
possible.

## Versioning Pipelines

You might have noticed that each time you run a pipeline in ZenML with the same name, but with
different configurations, it creates a new *version*, noticeable in the version column in the
[dashboard](dashboard.md). This turns out to be quite important when iterating over pipelines, but
still keeping track of all the work being done. Consider our example pipeline:

```python
first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=parameterized_svc_trainer(SVCTrainerParams(gamma=0.01)),
)

first_pipeline_instance.run()
```

Running this the first time will create a single `run` for `version 1` of the pipeline called `first_pipeline`. In case you did not run this in the first chapter, try it yourself:

```shell
python run.py --simple
```

If you do it again with different [runtime parameters](parameters.md):

```python
first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=parameterized_svc_trainer(SVCTrainerParams(gamma=0.02)),  # Changed!
)

first_pipeline_instance.run()
```

Try it yourself:

```python
python run.py --simple --gamma 0.02
```

This will create *yet another* `run` for `version 1` of the pipeline called `first_pipeline`. So
now the same pipeline has two runs.

However, now let's change the pipeline configuration itself. You can do this by either modifying
the step connections within the `@pipeline` function or replace a concrete step with another one.
For example, let's replace the `parameterized_svc_trainer` with another function that has the same signature but different name and logic:

```python
@step
def parameterized_tree_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier with hyper-parameters."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = DecisionTreeClassifier() # Changed!
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model


first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=parameterized_tree_trainer(),
)

first_pipeline_instance.run()
```

Try it yourself:

```python
python run.py --simple --trainer decision_tree
```

This will now create a single `run` for `version 2` of the pipeline called `first_pipeline`. This
way, you can continuously update a pipeline as you iterate, and not lose velocity, all the while
ensuring that when you do get to production it should make things easier.

You might also notice that running the above pipelines in that order actually got faster as you went through them. Which brings us to...

## Caching in ZenML

While iterating through experiments as pipelines in ZenML,
one need not process the data again and again that has already been computed in the pipeline. This is where caching kicks in and brings enormous benefits!

When you tweaked the `gamma` variable in the [previous chapter](./parameters.md), you must have noticed that the 
`simple_data_splitter` step does not re-execute for each subsequent run.  This is because ZenML 
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

You can try to disable caching and see how the runtime of the pipeline changes:

```python
python run.py --simple --no-cache
```

### Configuring caching behavior of your pipelines

Although caching is desirable in many circumstances, one might want to disable
it in certain instances. For example, if you are quickly prototyping with
changing step definitions or you have an external API state change in your
function that ZenML does not detect.

There are multiple ways to take control of when and where caching is used:
- [Configuring caching for the entire pipeline](#configuring-caching-for-the-entire-pipeline):
Do this if you want to configure caching for all steps of a pipeline.
- [Configuring caching for individual steps](#configuring-caching-for-individual-steps):
Do this to configure caching for individual steps. This is, e.g., useful to 
disable caching for steps that depend on external input.
- [Dynamically configuring caching for a pipeline run](#dynamically-configuring-caching-for-a-pipeline-run):
Do this if you want to change the caching behaviour at runtime. This is, e.g.,
useful to force a complete rerun of a pipeline.

#### Configuring caching for the entire pipeline

On a pipeline level, the caching policy can be set as a parameter within the
`@pipeline` decorator as shown below:

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

The setting above will disable caching for all steps in the pipeline, unless a 
step explicitly sets `enable_cache=True` (see below).

#### Configuring caching for individual steps

Caching can also be explicitly configured at a step level via a parameter of the
`@step` decorator:

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
```

The code above turns caching off for this step only. This is very useful in
practice since you might want to turn off caching for certain steps that take 
external input (like fetching data from an API or File IO) without affecting the
overall pipeline caching behaviour.

{% hint style="info" %}
You can get a graphical visualization of which steps were cached using
the [ZenML Dashboard](./pipelines.md).
{% endhint %}

#### Dynamically configuring caching for a pipeline run

Sometimes you want to have control over caching at runtime instead of defaulting
to the hard-coded pipeline and step decorator settings.
ZenML offers a way to override all caching settings at runtime:

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

The code above disables caching for all steps of your pipeline, no matter what
you have configured in the `@step` or `@parameter` decorators.

### Code Example

The following example shows caching in action with the code example from the
starter guide.

For a more detailed example on how caching is used at ZenML and how it works
under the hood, check out 
[ZenBytes lesson 1.2](https://github.com/zenml-io/zenbytes/blob/main/1-2_Artifact_Lineage.ipynb)!

<details>
<summary>Code Example of this Section</summary>

```python
pd.DataFrame
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.steps import BaseParameters, Output, step
from zenml.pipelines import pipeline

class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001


@step
def simple_data_splitter() -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame):
    # Load the wine dataset
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set


@step(enable_cache=False)  # never cache this step, always retrain
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


@pipeline
def first_pipeline(step_1, step_2):
    train_set, test_set = step_1()
    step_2(train_set, test_set)


first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=parameterized_svc_trainer(),
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
Step simple_data_splitter has started.
Step simple_data_splitter has finished in 0.135s.
Step parameterized_svc_trainer has started.
Step parameterized_svc_trainer has finished in 0.109s.
Pipeline run first_pipeline-07_Jul_22-12_05_54_573248 has finished in 0.417s.
```

#### Expected Output Run 2:

```
Creating run for pipeline: first_pipeline
Cache enabled for pipeline first_pipeline
Using stack default to run pipeline first_pipeline...
Step simple_data_splitter has started.
Using cached version of simple_data_splitter.
Step simple_data_splitter has finished in 0.014s.
Step parameterized_svc_trainer has started.
Step parameterized_svc_trainer has finished in 0.051s.
Pipeline run first_pipeline-07_Jul_22-12_05_55_813554 has finished in 0.161s.
```

#### Expected Output Run 3:

```
Creating run for pipeline: first_pipeline
Cache enabled for pipeline first_pipeline
Using stack default to run pipeline first_pipeline...
Runtime configuration overwriting the pipeline cache settings to enable_cache=False for this pipeline run. The default caching strategy is retained for future pipeline runs.
Step simple_data_splitter has started.
Step simple_data_splitter has finished in 0.078s.
Step parameterized_svc_trainer has started.
Step parameterized_svc_trainer has finished in 0.048s.
Pipeline run first_pipeline-07_Jul_22-12_05_56_718489 has finished in 0.219s.
```

</details>

