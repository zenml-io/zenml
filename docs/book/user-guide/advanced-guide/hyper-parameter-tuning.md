---
description: Running a hyper-parameter tuning trial with ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Hyper-parameter tuning

A basic iteration through a number of hyper-parameters can be achieved with ZenML by using a simple pipeline like this:

```python
@pipeline
def my_pipeline(step_count: int) -> None:
    data = load_data_step()
    after = []
    for i in range(step_count):
        train_step(data, learning_rate=i * 0.0001, name=f"train_step_{i}")
        after.append(f"train_step_{i}")
    model = select_model_step(..., after=after)
```

This is an implementation of a basic grid search (across a single dimension) that would allow for a different learning rate to be used across the same `train_step`. Once that step has been run for all the different learning rates, the `select_model_step` is a way to decide which of the hyper-parameters gave the best results or performance.

Grid search involves defining a grid of possible values for each hyperparameter and then systematically searching through this grid to find the best combination of hyperparameters that yields the highest performance metric, such as accuracy or F1 score.

The key thing to know here is that the `select_model_step` is a way to decide which step offers the best results (as you have defined them). Internally, such a step would need to access the outputs of the previous steps. For example, you can access the outputs of the current run with the following code:

```python
from zenml.environment import Environment
from zenml.post_execution import get_run

run_name = Environment().step_environment.run_name
run = get_run(run_name)

outputs = [
    {k: v.read() for k, v in s.outputs.items()}
    for s in run.steps
]
```

The outputs of the steps themselves can be accessed from the `.steps` property of the `run` object, and you can filter those in whatever way is appropriate for your use case. For a more sophisticated example of how to implement hyper-parameter tuning, see [our Dynamic Pipelines example](https://github.com/zenml-io/zenml/tree/main/examples/dynamic\_pipelines).

Hyper-parameter tuning is not yet a first-class citizen in ZenML, but it is [(high up) on our roadmap of features](https://zenml.hellonext.co/p/enable-hyper-parameter-tuning) that are due for implementation in an integrated way. In the meantime, the above is a way to achieve the same functionality.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
