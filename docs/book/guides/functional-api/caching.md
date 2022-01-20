---
description: Leverage caching.
---

# Caching

If you want to see the code for this chapter of the guide, head over to the 
[GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide/chapter\_4.py).

## Caching in action

What if we don't want to use TensorFlow but rather a [scikit-learn](https://scikit-learn.org) model? This is easy to 
do. Swap out implementations of individual steps and see caching save you time and money!

### Create steps

We add two more steps, a scikit-learn version of the `trainer` and `evaluator` step.

#### Trainer

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression
from zenml.steps import step

@step
def sklearn_trainer(
    config: TrainerConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train SVC from sklearn."""
    clf = LogisticRegression(penalty="l1", solver="saga", tol=0.1)
    clf.fit(X_train.reshape((X_train.shape[0], -1)), y_train)
    return clf
```

A simple enough step using a sklearn `ClassifierMixin` model. ZenML also knows how to store all primitive sklearn 
model types.

#### Evaluator

We also add a simple evaluator:

```python
@step
def sklearn_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate accuracy score with classifier."""

    test_acc = model.score(X_test.reshape((X_test.shape[0], -1)), y_test)
    return test_acc
```

#### Pipeline

And now the cool bit: We don't need to change the structure of the pipeline. We just need to change the concrete 
functions that implements the `trainer` and `evaluator` step:

```python
# Run the pipeline
mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(config=TrainerConfig()),
    evaluator=sklearn_evaluator(),
).run()
```

### Run

You can run this as follows:

```python
python chapter_4.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
...
Creating pipeline: mnist_pipeline
Cache enabled for pipeline `mnist_pipeline`
Using orchestrator `local_orchestrator` for pipeline `mnist_pipeline`. Running pipeline..
Step `importer_mnist` has started.
Step `importer_mnist` has finished in 0.032s.
Step `normalize_mnist` has started.
Step `normalize_mnist` has finished in 0.029s.
Step `sklearn_trainer` has started.
Step `sklearn_evaluator` has started.
Step `sklearn_evaluator` has finished in 0.191s.
```

Note that the `importer` and `normalize` steps are now **100x** faster. This is because we have not changed the 
pipeline itself, and just made another run with a different functions. So ZenML caches the unchanged steps and skips 
straight to the new trainer and evaluator.

### Inspect

If you add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
print(f"Pipeline `mnist_pipeline` has {len(p.runs)} run(s)")
for r in p.runs[0:2]:
    eval_step = r.get_step("evaluator")
    print(
        f"For {eval_step.entrypoint_name}, the accuracy is: "
        f"{eval_step.output.read():.2f}"
    )
```

You get the following output:

```bash
Pipeline `mnist_pipeline` has 2 run(s)
For tf_evaluator, the accuracy is: 0.91
For sklearn_evaluator, the accuracy is: 0.92
```

Looks like sklearn narrowly beat TensorFlow in this one. Within our `not_so_quickstart` 
[example](https://github.com/zenml-io/zenml/tree/main/examples/not\_so\_quickstart) we expand on this with a 
PyTorch example.

Combining different complex steps with standard pipeline interfaces is a powerful tool in any MLOps setup. You can 
now organize, track, and manage your codebase as it grows with your use-cases.
