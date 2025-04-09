---
description: Speed running to a pipeline run in your cloud.
icon: hand-wave
---

# Hello World

{% stepper %}
{% step %}
### Install ZenML

You can start by installing ZenML in a fresh new environment.

```bash
pip install zenml
```
{% endstep %}

{% step %}
### Write your first pipeline

Now, you can create a simple `run.py` file that defines your workflow using our Python SDK:

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
{% endstep %}

{% step %}
### Create your ZenML account

You can create [your ZenML Pro account](https://zenml.io/pro) here. No worries, it comes with a 14-day free trial without requiring any payment information. This way, you will have access to our Pro Dashboard, which can help you manage all the resources related to your ML workflows:

<figure><img src="../.gitbook/assets/dcp_walkthrough.gif" alt=""><figcaption></figcaption></figure>

If this is your first time logging in to ZenML Pro, you will have to set up a workspace and project. Keep in mind that this might take a few minutes. In the meanwhile, we would recommend going through the [Core Concepts](core-concepts.md) in ZenML. Once the workspace is set, you can do:&#x20;

```bash
zenml login  # Select your workspace here

zenml project set <PROJECT_NAME>  # Activate your project here
```
{% endstep %}

{% step %}
### Create your first remote stack

In ZenML, there are various ways to create and deploy a remote stack.&#x20;

<figure><img src="../.gitbook/assets/Screenshot 2025-04-09 at 14.56.35.png" alt=""><figcaption></figcaption></figure>

One of the quickest ways to do so is to use the Infrastructure-as-code option. This option uses Terraform modules provided by ZenML to deploy the required infrastructure and register it back to your ZenML server. To be able to do this, you need to:

* Have [Terraform](https://www.terraform.io/downloads.html) installed on your machine (version at least 1.9).
* Authenticate with your cloud provider through the provider's CLI or SDK tool.
* Have permissions to create the resources that the modules will provision.
{% endstep %}

{% step %}
### Run your pipeline on the remote stack

All you have to do to run the same pipeline on this new stack is to activate your new stack:

```bash
zenml stack set <NAME_OF_YOUR_NEW_STACK>
```

and run the same code without changing anything in its implementation:

```bash
python run.py
```

Once you run it, you can see the pipeline and the corresponding resources on the dashboard:

<figure><img src="../.gitbook/assets/Screenshot 2025-04-09 at 15.02.42.png" alt=""><figcaption></figcaption></figure>
{% endstep %}

{% step %}
### What's next?

By following this quick tutorial, you have:

* Created your ZenML Pro account and have access to our dashboard&#x20;
* Implemented your first pipeline using our Python SDK
* Deployed and registered your first remote stack
* Ran the same pipeline both locally and on a remote stack with a simple command&#x20;

What we recommend as the next steps:

* Learn more about how you can design and configure ZenML pipelines and steps to use advanced features like scheduling and caching
* How ZenML stores, versions and tracks your data as artifacts
* How you can organize your resources with tags and metadata
* Understand how ZenML deals with containerization and how you can utilize code repositories
* Understand how the concept of stacks work and how we handle their authentication through service connectors
* How to handle secrets&#x20;
* How to create blueprints of your pipeline runs with run templates
{% endstep %}
{% endstepper %}
