---
description: Add some normalization
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

# Chapter 3: Train and evaluate the model.

Finally we can train and evaluate our model. 
## Create steps

For this we decide to add two steps, a `trainer` and an `evaluator` step. We also keep using Tensorflow to help with these.

### Trainer

```python
import numpy as np
import tensorflow as tf

from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig

class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 1
    gamma: float = 0.7
    lr: float = 0.001
    
@step
def tf_trainer(
    config: TrainerConfig,  # not an artifact, passed in when 
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognise MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10, activation="relu"),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        X_train,
        y_train,
        epochs=config.epochs,
    )

    # write model
    return model
```

A few things of note:

* This would be first instance of `parameterizing` a step with a `BaseStepConfig`. This allows us to specify some parameters at run-time rather than via data artifacts between steps.
* This time the trainer returns a `tf.keras.Model`, which ZenML takes care of storing in the artifact store. We will talk about how to 'take over' this storing via `Materializers` in a later chapter.

### Evaluator
We also add a a simple evaluator:

```python
@step
def tf_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""

    _, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc
```

This gets the model and test data, and calculate simple model accuracy over the test set.

### Pipeline

And now our pipeline looks like this:

```python
@pipeline
def mnist_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    X_train, y_train, X_test, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)
```

We can run it with the concrete functions:

```python
# Run the pipeline
mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalize_mnist(),
    trainer=tf_trainer(config=TrainerConfig(epochs=1)),
    evaluator=tf_evaluator(),
).run()
```

Beautiful, now the pipeline is truly doing something. Let's run it!

## Run
You can run this as follows:

```python
python chapter_3.py
```
And see the output as follows:

```bash
Creating pipeline: mnist_pipeline
Cache enabled for pipeline `mnist_pipeline`
Using orchestrator `local_orchestrator` for pipeline `mnist_pipeline`. Running pipeline..
Step `importer_mnist` has started.
Step `importer_mnist` has finished in 1.819s.
Step `normalize_mnist` has started.
Step `normalize_mnist` has finished in 2.036s.
Step `tf_trainer` has started.
2021-10-21 13:24:30.842732: W tensorflow/core/framework/cpu_allocator_impl.cc:80] Allocation of 188160000 exceeds 10% of free system memory.
2021-10-21 13:24:31.096714: I tensorflow/compiler/mlir/mlir_graph_optimization_pass.cc:185] None of the MLIR Optimization Passes are enabled (registered 2)
1875/1875 [==============================] - 3s 1ms/step - loss: 0.5092 - accuracy: 0.8567
2021-10-21 13:24:33.903987: W tensorflow/python/util/util.cc:348] Sets are not currently considered sequences, but this may change in the future, so consider avoiding using them.
Step `tf_trainer` has finished in 4.723s.
Step `tf_evaluator` has started.
I1021 13:24:34.296284  4468 rdbms_metadata_access_object.cc:686] No property is defined for the Type
313/313 - 0s - loss: 0.3106 - accuracy: 0.9100
`tf_evaluator` has finished in 0.742s.```
```

## Inspect 

If you add the following code to fetch the pipeline:

```python
from zenml.core.repo import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
runs = p.get_runs()
print(f"Pipeline `mnist_pipeline` has {len(runs)} run(s)")
run = runs[0]
print(f"The first run has {len(run.steps)} steps.")
step = run.steps[3]
print(
    f"The step has an evaluator step with accuracy: {step.outputs[0].read(None)}"
)
```

You get the following output:

```bash
Pipeline `mnist_pipeline` has 1 run(s)
The first run has 4 steps.
The step has an evaluator step with accuracy: 0.9100000262260437
```

Wow, we just trained our first model! But have not stopped yet. What if did not want to use Tensorflow? Let's swap out our trainers and evaluators for different libraries.