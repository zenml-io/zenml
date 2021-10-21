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

# Chapter 4: Swap out implementations of individual steps and see caching in action

What if we don't want to use Tensorflow but rather a [scikit-learn](https://scikit-learn.org/) model? This is easy to do.

## Create steps

We add two more steps, a scikit-learn version of the `trainer` and `evaluator` step.

### Trainer

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

A simple enough step using a sklearn `ClassifierMixin` model. ZenML also knows how to store all primitive sklearn model types.

### Evaluator
We also add a a simple evaluator:

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

### Pipeline

And now the cool bit: We don't need to change the pipeline at all. We just need to change the concrete functions:

```python
# Run the pipeline
mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(config=TrainerConfig()),
    evaluator=sklearn_evaluator(),
).run()
```

## Run
You can run this as follows:

```python
python chapter_4.py
```
And see the output as follows:

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

Note that the `importer` and `mnist` steps are now a **100x** faster. This is because we have not changed the pipeline at all, and just made another run with different functions. So ZenML caches these steps and skips straight to the new trainer and evaluator.

## Inspect 

If you add the following code to fetch the pipeline:

```python
from zenml.core.repo import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="mnist_pipeline")
print(f"Pipeline `mnist_pipeline` has {len(p.get_runs())} run(s)")
for r in p.get_runs()[0:2]:
    eval_step = r.steps[3]
    print(
        f"For {eval_step.name}, the accuracy is: "
        f"{eval_step.outputs[0].read(None):.2f}"
    )
```

You get the following output:

```bash
Pipeline `mnist_pipeline` has 2 run(s)
For tf_evaluator, the accuracy is: 0.91
For sklearn_evaluator, the accuracy is: 0.92
```

Looks like sklearn narrowly beat tensorflow in this one. If we want we can keep extending this and add a PyTorch example (we have done with the `not_so_quickstart` [example](https://github.com/zenml-io/zenml/tree/main/examples/not_so_quickstart)). 

Combining different complex steps with standard pipeline interfaces is a powerful tool in any MLOps setup. You can now organize, track, and manage your codebase as it grows with your use-cases.