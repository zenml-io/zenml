---
description: Welcome to ZenML!
---

# ⭐ Introduction

🤹 Are you an ML engineer or data scientist shipping models to production while juggling a plethora of tools?

🤷‍♂️ Do you struggle with versioning data, code, and models in your projects?

👀 Have you had trouble replicating production pipelines and monitoring models in production?

[🙇](https://apps.timwhitlock.info/emoji/tables/unicode#emoji-modal) Are you dealing with lots of unstructured notebooks or scripts with lots of manual processes?

[🚧](https://apps.timwhitlock.info/emoji/tables/unicode#emoji-modal) Do you find it challenging to transition your ML workflows from the experimentation setting to a production-ready environment?

If you answered yes to any of the questions above, ZenML is here to help you:

**ZenML** is an extensible, open-source MLOps framework for creating portable, 
production-ready MLOps pipelines. 

By decoupling infrastructure from code, ZenML gives all ML developers in your 
organization more freedom and independence in how they approach their work:

![ZenML Overview](.gitbook/assets/intro_zenml_overview.png)

{% tabs %}

{% tab title="ZenML for MLOps / Platform Engineers" %}

As an MLOps infrastructure expert, ZenML enables you to define, deploy, and 
manage sophisticated production environments that are easy to share with your 
colleagues.

**Standardization:** With ZenML, you can standardize MLOps infrastructure and 
tooling across your organization. Simply set up a ZenML server, register your 
production environment as a ZenML stack, and invite your colleagues to run 
their ML workflows on it:

```bash
zenml deploy  # Deploy ZenML
zenml stack register production ...  # Register your production environment
zenml stack share production  # Make it available to your colleagues
```

**No Vendor Lock-In:** Since infrastructure is decoupled from code, ZenML gives
you the freedom to switch to a different tooling stack whenever it suits you.
By avoiding vendor lock-in, you have the flexibility to transition between 
various cloud providers or services, ensuring that you receive the best 
performance and pricing available in the market at any time.

```bash
zenml stack set gcp
python run.py  # Run your ML workflows in GCP
zenml stack set aws
python run.py  # Now your ML workflow runs in AWS
```

**Extensibility:** ZenML is open-source and highly extensible, so you benefit 
from industry-standard best-practices built into the framework while also being 
able to customize it to fit your specific needs.

{% endtab %}

{% tab title="ZenML for ML Engineers" %}

As an ML Engineer, ZenML enables you take ownership of the entire ML workflow
end-to-end. Adopting ZenML means fewer handover points and more visibility on
what is happening in your organization.

**ML Lifecycle Management:** ZenML's abstractions make it possible to manage the
entire ML lifecycle of your company end-to-end. Complex infrastructure setups 
are bundled into "stacks" and sophisticated ML workflows into "pipelines",
enabling you to move ML workflows between different environments in seconds.

**Reproducibility:** ZenML enables you to painlessly reproduce previous results
by automatically tracking and versioning stacks, pipelines, and output 
artifacts. In the ZenML dashboard you can get an overview of everything that has happened. Try it out on https://demo.zenml.io/!

**Automated Deployments:** With ZenML you no longer need to upload custom 
Docker images to the cloud every time you want to deploy a new model to 
production. Simply define your ML workflow as a ZenML pipeline, let ZenML 
handle all the containerization, and have your model automatically deployed to 
a highly scalable Kubernetes deployment service like 
[Seldon](./user-guide/component-galery/model-deployers/seldon.md).

{% endtab %}

{% tab title="ZenML for Data Scientists" %}

As a Data Scientist, ZenML gives you the freedom to focus on modeling and
experimentation while writing code that is immediately production-ready.

**Develop Locally:** Since ZenML code runs in any environment, you can 
develop ML models locally with all your favorite tools. Once you are happy with 
your results, you can switch to a production environment via a single command 
and all your code will just work:

```bash
python run.py  # develop your code locally with all your favorite tools
zenml stack set production
python run.py  # run on production infrastructure without any code changes
```

**Pythonic SDK:** ZenML is designed to be as unintrusive as possible. Adding 
a ZenML `@step` or `@pipeline` decorator to your Python functions is enough to 
turn your existing code into ZenML pipelines:

```python
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

**Reusability:** Defining your code as ZenML steps brings standardization 
into your organization, allowing you to easily reuse code developed by your 
colleagues:

```python
from my_organization.steps import data_loader_step, model_validation_step

@step
def my_model_trainer_step(data):
    ...

@pipeline
def my_pipeline():
  data = data_loader_step()
  model = my_model_trainer_step(data)
  eval_metric = model_validation_step(model)
```
{% endtab %}

{% endtabs %}

## Directions

Ready to harness the power of ZenML for your machine learning projects? Here is a collection of pages you can take a look at next:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f4bf">💿</span> <strong>Installation</strong></td><td>Install ZenML to get started.</td><td></td><td><a href="getting-started/installation.md">installation.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f9f1">🧱</span> <strong>Core Concepts</strong></td><td>Understand the core concepts behind ZenML.</td><td></td><td><a href="getting-started/core-concepts.md">core-concepts.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f423">🐣</span> <strong>Starter Guide</strong></td><td>Get started quickly with a simple setup.</td><td></td><td></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f414">🐔</span> <strong>Advanced Guide</strong></td><td>Hone your MLOps skills with an advanced guide.</td><td></td><td></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f4cb">📋</span> <strong>Component Guide</strong></td><td>Browse through the already-implemented integrations for ZenML.</td><td></td><td><a href="user-guide/component-galery/">component-galery</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f3d7">🏗</span> <strong>Set up your MLOps Platform</strong></td><td>Establish your production-ready infrastructure.</td><td></td><td><a href="platform-guide/set-up-your-mlops-platform/">set-up-your-mlops-platform</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f9d1-1f692">🧑🚒</span> <strong>Manage the Deployed Services</strong></td><td>Manage your production-ready infratstructure.</td><td></td><td><a href="platform-guide/manage-the-deployed-services/">manage-the-deployed-services</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f9d1-1f3eb">🧑🏫</span> <strong>Examples</strong></td><td>Take a peek at how ZenML works in concrete examples.</td><td></td><td><a href="learning/examples/">examples</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f64b">🙋</span> <strong>FAQ</strong></td><td>Find the answers to the most frequently asked questions.</td><td></td><td><a href="learning/faq.md">faq.md</a></td></tr></tbody></table>
