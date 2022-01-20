---
description: Train some models.
---

# Train & Evaluate

If you want to see the code for this chapter of the guide, head over to the 
[GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide/chapter\_3.py).

## Train and evaluate the model

Finally, we can train and evaluate our model.

### Create steps

For this we decide to add two steps, a `trainer` and an `evaluator` step. We also keep using TensorFlow to help 
with these.

#### Trainer

```python
import numpy as np
import tensorflow as tf

from zenml.steps import step, BaseStepConfig

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
    """Train a neural net from scratch to recognize MNIST digits return our
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

    # model just needs to be returned, zenml takes care of persisting the model 
    return model
```

A few things of note:

* This is our first instance of `parameterizing` a step with a `BaseStepConfig`. This allows us to specify some 
parameters at run-time rather than via data artifacts between steps.
* This time the trainer returns a `tf.keras.Model`, which ZenML takes care of storing in the artifact store. We will 
talk about how to 'take over' this storing via `Materializers` in a later [chapter](materialize-artifacts.md).

#### Evaluator

We also add a a simple evaluator:

```python
@step
def tf_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model on the test set"""

    _, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc
```

This gets the model and test data, and calculates simple model accuracy over the test set.

#### Pipeline

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

### Run

You can run this as follows:

```python
python chapter_3.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating pipeline: mnist_pipeline
Cache enabled for pipeline `mnist_pipeline`
Using orchestrator `local_orchestrator` for pipeline `mnist_pipeline`. Running pipeline..
Step `importer_mnist` has started.
Step `importer_mnist` has finished in 1.819s.
Step `normalize_mnist` has started.
Step `normalize_mnist` has finished in 2.036s.
Step `tf_trainer` has started.
Step `tf_trainer` has finished in 4.723s.
Step `tf_evaluator` has started.
`tf_evaluator` has finished in 0.742s.
```

### Inspect

If you add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
runs = p.runs
print(f"Pipeline `mnist_pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} steps.")
step = run.get_step('evaluator')
print(
    f"The `tf_evaluator step` returned an accuracy: {step.output.read()}"
)
```

You get the following output:

```bash
Pipeline `mnist_pipeline` has 1 run(s)
The first run has 4 steps.
The `tf_evaluator step` returned an accuracy: 0.9100000262260437
```

Wow, we just trained our first model! But have not stopped yet. What if did not want to use TensorFlow? Let's swap 
out our trainers and evaluators for different libraries.
