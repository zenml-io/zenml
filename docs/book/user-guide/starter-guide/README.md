# 🐣 Starter Guide

ZenML helps you standardize your ML workflows as **Pipelines** consisting of decoupled, modular **Steps**. This enables you to write portable code that can be moved from experimentation to production in seconds.

### Pipeline

The simplest ZenML pipeline could look like this:

```python
from zenml.pipelines.new import pipeline
from zenml.steps import step

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

if __name__ == "__main__":
  my_pipeline()
```

{% hint style="info" %}
* `@step` is a decorator that converts its function into a step that can be used within a pipeline
* `@pipeline` defines a function as a pipeline
  * within this function the steps are called and their outputs are routed
{% endhint %}

Copy this code into a file main.py and run it.

{% code overflow="wrap" %}
```bash
$ python main.py

Registered pipeline my_pipeline (version 1).
Running pipeline my_pipeline on stack default (caching enabled)
Step step_1 has started.
Step step_1 has finished in 0.121s.
Step step_2 has started.
helloworld
Step step_2 has finished in 0.046s.
Pipeline run my_pipeline-... has finished in 0.676s.
Pipeline visualization can be seen in the ZenML Dashboard. Run zenml up to see your pipeline!
```
{% endcode %}

In the output, there's a line with something like this.

{% code overflow="wrap" %}
```bash
Pipeline visualization can be seen in the ZenML Dashboard. Run zenml up to see your pipeline!
```
{% endcode %}

ZenML offers you a comprehensive Dashboard to interact with your Pipelines, Artifacts and Infrastructure. To see it, simply deploy the ZenML service locally in the next section.

### Explore the Dashboard

Run `zenml up` in the environment where you have ZenML installed.

After a few seconds your browser should open the ZenML Dashboard for you at [http://127.0.0.1:8237/](http://127.0.0.1:8237/)

The default user account is **Username**: _**default**_ with no password.

<figure><img src="../../.gitbook/assets/Dashboard.png" alt=""><figcaption><p>Landing Page of the Dashboard</p></figcaption></figure>

As you can see, the dashboard shows you that there is 1 pipeline and 1 pipeline run. (feel free to ignore the stack and components for the time being)

If you navigate to the run that you just executed, you will see a diagram view of the pipeline run, including a visualization of the data that is passed between the steps.

```
// Placeholder for Screenshot
```

## Recap

### Step

```python
@step
def step_2(input_one: str, input_two: str) -> None:
  combined_str = input_one + input_two
  return combined_str
```

Steps are functions. These functions have inputs and outputs. For ZenML to work properly, these need to be typed.

### Artifacts

The inputs and outputs of a step are called _artifacts._ They are automatically tracked and stored by ZenML in the artifact store. Artifacts are produced by and circulated among steps whenever your step returns an object or a value. This means the data is not passed between steps in memory. Rather at the output of a step they are written to storage and at the input of the step they are loaded from storage.

### Pipeline

```python
@pipeline
def my_pipeline():
  output_step_one = step_1()
  step_2(input_one="hello", input_two=output_step_one)
```

Pipelines are also functions. However you are only allowed to call steps within this function. The inputs for steps within a function can either be the outputs of previous steps, or alternatively you can pass in values directly.

### Executing the Code

```python
if __name__ == "__main__":
  my_pipeline()
```

Executing the Pipeline is as easy as just calling the function.



## Whats next?

...
