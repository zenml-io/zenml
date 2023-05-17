---
description: Run a hyper-parameter tuning trial with ZenML
---

# Hyper-parameter tuning in ZenML

# TODO 

This page is supposed to talk about how a simple pipeline like this can be used to do rough grid search through
a list of parameters.

Its very basic, but gets some of the job done.


```python
@pipeline
def my_pipeline(step_count: int) -> None:
  data = load_data_step()
  after = []
  for i in range(step_count):
    train_step(data, learning_rate=i*0.0001, name=f"train_step_{i}")
    after.append(f"train_step_{i}")
  model = select_model_step(..., after=after)
```

The trick here is the `select_model_step` which inside it needs to fetch all the steps wth the client,
something like this but a bit refined:

```python
def gather_dictionaries(
    gather_steps_params: GatherStepsParameters,
) -> List[dict]:
    """Extract the output of steps compatible with the parameters of
    gather_steps_params.

    Args:
        gather_steps_params: The parameters object to filter the relevant
            steps.

    Returns:
        A list of dictionaries of the outputs of the steps.
    """
    run_name = Environment().step_environment.run_name
    run = get_run(run_name)
    prefix_steps = (
        [
            s
            for s in run.steps
            if s.name.startswith(gather_steps_params.output_steps_prefix)
        ]
        if gather_steps_params.output_steps_prefix is not None
        else []
    )

    named_steps = (
        [
            s
            for s in run.steps
            if s.name in gather_steps_params.output_steps_names
        ]
        if gather_steps_params.output_steps_names is not None
        else []
    )

    return [
        {k: v.read() for k, v in s.outputs.items()}
        for s in prefix_steps + named_steps
    ]
```

End chapter with the fact that this will be improved later on in ZenML.

# ENDTODO