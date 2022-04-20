---
description: Create your first step.
---

# Create steps

Steps are the atomic components of a ZenML pipeline. Each step is defined by its inputs, the logic it applies and its 
outputs. Here is a very simple example of such a step:

{% tabs %}
{% tab title="Single Output" %}
```python
from zenml.steps import step

@step
def my_first_step() -> int:
    """Step that returns a pre-defined integer"""
    return 7
```
{% endtab %}

{% tab title="Multiple Outputs" %}
```python
from zenml.steps import step, Output

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1
```

- As this step has multiple outputs, we need to use the `zenml.steps.step_output.Output` class to indicate the names 
of each output. If there was only one, we would not need to do this.
{% endtab %}

Now we can go ahead and create a pipeline with one step to make sure this step works:

```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(
    first_step,
):
    """The simplest possible pipeline"""
    # We just need to call the function
    first_step()

# run the pipeline
first_pipeline(first_step=my_first_step()).run()
```


The output will look as follows (note: this is filtered to highlight the most important logs)

```bash
Creating run for pipeline: `first_pipeline`
Cache disabled for pipeline `first_pipeline`
Using stack `default` to run pipeline `first_pipeline`
Step `my_first_step` has started.
Step `my_first_step` has finished in 0.048s.
Pipeline run `first_pipeline-20_Apr_22-14_17_42_279890` has finished in 0.057s.
```

## Inspect

You can add the following code to fetch the pipeline:

```python
from zenml.repository import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="load_mnist_pipeline")
runs = p.runs
print(f"Pipeline `load_mnist_pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} step(s).")
step = run.get_step('importer')
print(f"That step has {len(step.outputs)} output artifacts.")
for k, o in step.outputs.items():
    arr = o.read()
    print(f"Output '{k}' is an array with shape: {arr.shape}")
```

You will get the following output:

```bash
Pipeline `load_mnist_pipeline` has 1 run(s).
The run you just made has 1 step(s).
That step has 4 output artifacts.
Output 'X_test' is an array with shape: (10000, 28, 28)
Output 'y_test' is an array with shape: (10000,)
Output 'y_train' is an array with shape: (60000,)
Output 'X_train' is an array with shape: (60000, 28, 28)
```

So now we have successfully confirmed that the data is loaded with the right shape and we can fetch it again from 
the artifact store.
