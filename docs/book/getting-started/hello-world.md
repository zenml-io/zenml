---
description: Discovering the core concepts behind ZenML.
icon: hand-wave
---

# Hello World

### Install ZenML

[Install ZenML](installation.md) in a fresh environment.

```
pip install zenml
```

### Write your pipeline

Create a `run.py` file that defines your workflow using our Python SDK:

<pre class="language-python"><code class="lang-python">from zenml import step, pipeline


@step
def basic_step() -> str:
    return "Hello World!"


@pipeline
def basic_pipeline():
    basic_step()


if __name__ == "__main__":
<strong>    basic_pipeline()
</strong></code></pre>

{% hint style="success" %}
If you would like to, you can already run this pipeline locally with `python run.py`
{% endhint %}

### Deploy the stack

Through this dashboard, you can deploy a cloud stack of your choice:



To deploy the cloud stack,  you need to have Terraform installed on your machine. Also, you need to be authenticated with the respective CLI tooling of the cloud provider of your choice.&#x20;

{% hint style="warning" %}
Following this step will create resources on your cloud.
{% endhint %}

### Run the pipeline

All you have to do to run this pipeline on your brand new stack is to set it.



### What did you just do?

* You implemented a simple pipeline using our Python SDK.&#x20;
* You deployed a stack on your desired cloud provider.&#x20;
* You ran&#x20;

### What else is there?

*
