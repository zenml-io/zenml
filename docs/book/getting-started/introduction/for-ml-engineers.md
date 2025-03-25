---
hidden: true
---

# For ML Engineers

ZenML empowers ML engineers to take ownership of the entire ML lifecycle end-to-end. Adopting ZenML means fewer handover points and more visibility on what is happening in your organization.

#### **ML Lifecycle Management**

ZenML's abstractions enable you to manage sophisticated ML setups with ease. After you define your ML workflows as [Pipelines](../core-concepts.md#1-development) and your development, staging, and production infrastructures as [Stacks](../core-concepts.md#2-execution), you can move entire ML workflows to different environments in seconds.

```bash
zenml stack set staging
python run.py  # test your workflows on staging infrastructure
zenml stack set production
python run.py  # run your workflows in production
```

#### **Reproducibility**

ZenML enables you to painlessly reproduce previous results by automatically tracking and versioning all stacks, pipelines, artifacts, and source code. In the ZenML dashboard, you can get an overview of everything that has happened and drill down into detailed lineage visualizations. Try it out at [https://www.zenml.io/live-demo](https://www.zenml.io/live-demo)!

<figure><img src="../../.gitbook/assets/Dashboard.png" alt="ZenML Dashboard Overview" width="563"><figcaption><p>Landing page for all your ML Engineering activities</p></figcaption></figure>

#### **Automated Deployments**

With ZenML, you no longer need to upload custom Docker images to the cloud whenever you want to deploy a new model to production. Simply define your ML workflow as a ZenML pipeline, let ZenML handle the containerization, and have your model automatically deployed to a highly scalable Kubernetes deployment service like [Seldon](../../component-guide/model-deployers/seldon.md).

```python
from zenml.integrations.seldon.steps import seldon_model_deployer_step
from my_organization.steps import data_loader_step, model_trainer_step

@pipeline
def my_pipeline():
  data = data_loader_step()
  model = model_trainer_step(data)
  seldon_model_deployer_step(model)
```

***

#### :rocket: **Learn More**

Ready to manage your ML lifecycles end-to-end with ZenML? Here is a collection of pages you can take a look at next:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th><th data-hidden data-card-cover data-type="files"></th></tr></thead><tbody><tr><td><strong>Starter Guide</strong></td><td>Get started with ZenML and learn how to build your first pipeline and stack.</td><td><a href="https://app.gitbook.com/s/75OYotLPi8TviSrtZTJZ/starter-guide">Starter guide</a></td><td><a href="../../.gitbook/assets/starter-guide.png">starter-guide.png</a></td></tr><tr><td><strong>How To</strong></td><td>Discover advanced ZenML features like config management and containerization.</td><td><a href="../../how-to/pipeline-development/build-pipelines/">build-pipelines</a></td><td><a href="../../.gitbook/assets/how-to.png">how-to.png</a></td></tr><tr><td><strong>Examples</strong></td><td>Explore ZenML through practical use-case examples.</td><td><a href="https://app.gitbook.com/s/75OYotLPi8TviSrtZTJZ/examples">Examples</a></td><td><a href="../../.gitbook/assets/examples.png">examples.png</a></td></tr></tbody></table>
