---
description: How to specify per-step resources
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Some steps of your machine learning pipeline might be more resource-intensive
and require special hardware to execute. In such cases, you can specify the 
required resources for steps as follows:

{% tabs %}
{% tab title="Functional API" %}

```python
from zenml.steps import step, ResourceConfiguration

@step(resource_configuration=ResourceConfiguration(cpu_count=8, gpu_count=2))
def training_step(...) -> ...:
    # train a model
```
{% endtab %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep, ResourceConfiguration

class TrainingStep(BaseStep):
    ...

step = TrainingStep(resource_configuration=ResourceConfiguration(cpu_count=8, gpu_count=2))
```
{% endtab %}
{% endtabs %}


{% hint style="info" %}
If you're using an orchestrator which doesn't support this feature or its underlying
infrastructure doesn't cover your requirements, you can also take a look at 
[step operators](../../mlops-stacks/step-operators/step-operators.md) which allow you to execute
individual steps of your pipeline in environments independent of your orchestrator. 
{% endhint %}
