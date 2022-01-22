---
description: Add some normalization
---

If you want to see the code for this chapter of the guide, head over to the
[GitHub](https://github.com/zenml-io/zenml/blob/main/examples/functional_api/chapter_2.py).

# Normalize the data

Now before writing any trainers we can actually normalize our data to make sure we get better results. To do this 
let's add another step and make the pipeline a bit more complex.

## Create steps

We can think of this as a `normalizer` step that takes data from the importer and normalizes it:

```python
# Add another step
@step
def normalize_mnist(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed
```

And now our pipeline looks like this:

```python
@pipeline
def load_and_normalize_pipeline(
    importer,
    normalizer,
):
    """Pipeline now has two steps we need to connect together"""
    X_train, y_train, X_test, y_test = importer()
    normalizer(X_train=X_train, X_test=X_test)
```

## Run

You can run this as follows:

```python
python chapter_2.py
```

The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating pipeline: load_and_normalize_pipeline
Cache enabled for pipeline `load_and_normalize_pipeline`
Using orchestrator `local_orchestrator` for pipeline `load_and_normalize_pipeline`. Running pipeline..
Step `importer_mnist` has started.
Step `importer_mnist` has finished in 1.751s.
Step `normalize_mnist` has started.
Step `normalize_mnist` has finished in 1.848s.
```

## Inspect

You can add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="load_and_normalize_pipeline")
runs = p.runs
print(f"Pipeline `load_and_normalize_pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} steps.")
step = run.get_step('normalizer')
print(f"The `normalizer` step has {len(step.outputs)} output artifacts.")
for k, o in step.outputs.items():
    arr = o.read()
    print(f"Output '{k}' is an array with shape: {arr.shape}")
```

You will get the following output:

```bash
Pipeline `load_and_normalize_pipeline` has 1 run(s)
The run you just made has 2 steps.
The `normalizer` step has 2 output artifacts.
Output 'X_train_normed' is an array with shape: (60000, 28, 28)
Output 'X_test_normed' is an array with shape: (10000, 28, 28)
```

Which confirms again that the data is stored properly! Now we are ready to create some trainers..
