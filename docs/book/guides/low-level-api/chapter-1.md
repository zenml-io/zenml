---
description: Create your  first step.
---

To follow along with the guide, best is to copy the code you see into your own local env and play along. To get started:

```bash
mkdir zenml_low_level_guide
cd zenml_low_level_guide
git init
zenml init
```

You can then put subsequent code in the right files.

If you just want to see the code for each chapter the guide, head over to the [GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide/).


# Chapter 1: Create an importer step to load data

The first thing to do is to load our data. We create a step that can load data from an external source (in this case a [Keras Dataset](https://keras.io/api/datasets/)). This can be done by creating a simple function and decorating it with the `@step` decorator.

## Create steps

```python
import numpy as np
import tensorflow as tf
from zenml.steps import step
from zenml.steps.step_output import Output

@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test
```

There are some things to note:

* As this step has multiple outputs, we need to use the `zenml.steps.step_output.Output` class to indicate the names of each output. If there was only one, we did not need to do this.
* We could have returned the `tf.keras.datasets.mnist` directly but we wanted to persist the actual data (for caching purposes), rather than the dataset object.

Now we can go ahead and create a pipeline with one step to make sure this step works:

```python
from zenml.pipelines import pipeline

@pipeline
def load_mnist_pipeline(
    importer,
):
    """The simplest possible pipeline"""
    # We just need to call the function
    importer()

# run the pipeline
load_mnist_pipeline(importer=importer_mnist()).run()
```

## Run
You can run this as follows:

```python
python chapter_1.py
```
And see the output as follows:

```bash
Creating pipeline: load_mnist_pipeline
Cache enabled for pipeline `load_mnist_pipeline`
Using orchestrator `local_orchestrator` for pipeline `load_mnist_pipeline`. Running pipeline..
Step `importer_mnist` has started.
Step `importer_mnist` has finished in 3.363s.
```

## Inspect 

If you add the following code to fetch the pipeline:

```python
repo = Repository()
p = repo.get_pipeline(pipeline_name="load_mnist_pipeline")
runs = p.get_runs()
print(f"Pipeline `load_mnist_pipeline` has {len(runs)} runs")
run = runs[0]
print(f"The first run has {len(run.steps)} steps.")
step = run.steps[0]
print(f"That step has {len(step.outputs)} output artifacts.")
for i, o in enumerate(step.outputs):
    arr = o.read(None)
    print(f"Output {i} is an array with shape: {arr.shape}")
```

You get the following output:

```bash
Pipeline `load_mnist_pipeline` has 1 run(s).
The first run has 1 steps.
That step has 4 output artifacts.
Output 0 is an array with shape: (60000,)
Output 1 is an array with shape: (10000,)
Output 2 is an array with shape: (10000, 28, 28)
Output 3 is an array with shape: (60000, 28, 28)
```

So now we have successfully confirmed that the data is loaded with the right shape and we can fetch it again from the artifact store.