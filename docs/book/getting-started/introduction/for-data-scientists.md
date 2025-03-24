---
hidden: true
---

# For Data Scientists

ZenML gives data scientists the freedom to fully focus on modeling and experimentation while writing code that is production-ready from the get-go.

#### Develop Locally

ZenML allows you to develop ML models in any environment using your favorite tools. This means you can start developing locally, and simply switch to a production environment once you are satisfied with your results.

```bash
python run.py  # develop your code locally with all your favorite tools
zenml stack set production
python run.py  # run on production infrastructure without any code changes
```

#### Pythonic SDK

ZenML is designed to be as unintrusive as possible. Adding a ZenML `@step` or `@pipeline` decorator to your Python functions is enough to turn your existing code into ZenML pipelines:

```python
from zenml import pipeline, step

@step
def step_1() -> str:
  return "world"

@step
def step_2(input_one: str, input_two: str) -> None:
  combined_str = input_one + ' ' + input_two
  print(combined_str)

@pipeline
def my_pipeline():
  output_step_one = step_1()
  step_2(input_one="hello", input_two=output_step_one)

my_pipeline()
```

#### Automatic Metadata Tracking

ZenML automatically tracks the metadata of all your runs and saves all your datasets and models to disk and versions them. Using the ZenML dashboard, you can see detailed visualizations of all your experiments.

{% hint style="info" %}
ZenML integrates seamlessly with many popular open-source tools, so you can also combine ZenML with other popular experiment tracking tools like [Weights & Biases](https://docs.zenml.io/stacks/experiment-trackers/wandb), [MLflow](https://docs.zenml.io/stacks/experiment-trackers/mlflow), or [Neptune](https://docs.zenml.io/stacks/experiment-trackers/neptune) for even better reproducibility.
{% endhint %}

***

#### :rocket: Learn More

Ready to develop production-ready code with ZenML? Here is a collection of pages you can take a look at next:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Core Concepts</strong></td><td>Understand the core concepts behind ZenML.</td><td><a href="../../.gitbook/assets/core-concepts.png">core-concepts.png</a></td><td><a href="../core-concepts.md">core-concepts.md</a></td></tr><tr><td><strong>Starter Guide</strong></td><td>Get started with ZenML and learn how to build your first pipeline and stack.</td><td><a href="../../.gitbook/assets/starter-guide.png">starter-guide.png</a></td><td><a href="https://app.gitbook.com/s/75OYotLPi8TviSrtZTJZ/starter-guide">Starter guide</a></td></tr><tr><td><strong>Quickstart (in Colab)</strong></td><td>Build your first ZenML pipeline and deploy it in the cloud.</td><td><a href="../../.gitbook/assets/quickstart.png">quickstart.png</a></td><td><a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb">https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb</a></td></tr></tbody></table>
