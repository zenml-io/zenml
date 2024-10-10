---
title: "Introduction"
description: "Welcome to ZenML!"
icon: star
mode: wide
---

**ZenML** is an extensible, open-source MLOps framework for creating portable, production-ready machine learning pipelines. By decoupling infrastructure from code, ZenML enables developers across your organization to collaborate more effectively as they develop to production.
<Frame caption="ZenML Overview">
  <img src=".gitbook/assets/intro_zenml_overview.png"/>
</Frame>
<br/>
<Tabs>
  <Tab title="For MLOps Platform Engineers">
ZenML enables MLOps infrastructure experts to define, deploy, and manage sophisticated production environments that are easy to share with colleagues.

* **ZenML Pro** **:** [ZenML Pro](/getting-started/deploying-zenml/zenml-pro/zenml-pro) provides a control plane that allows you to deploy a managed ZenML instance and get access to exciting new features such as CI/CD, Model Control Plane, and RBAC.
<Frame>
  <img src=".gitbook/assets/zenml-cloud-tenant-overview.png"/>
</Frame>
* **Self-hosted deployment:** ZenML can be deployed on any cloud provider and provides many Terraform-based utility functions to deploy other MLOps tools or even entire MLOps stacks:

```Bash
# Deploy ZenML to any cloud
zenml deploy --provider aws
# Connect cloud resources with a simple wizard
zenml stack register  --provider aws
# Deploy entire MLOps stacks at once
zenml stack deploy  --provider gcp
```
* **Standardization:** With ZenML, you can standardize MLOps infrastructure and tooling across your organization. Simply register your staging and production environments as ZenML stacks and invite your colleagues to run ML workflows on them.

```Bash
# Register MLOps tools and infrastructure
zenml orchestrator register kfp_orchestrator -f kubeflow
# Register your production environment
zenml stack register production --orchestrator kubeflow ...
```
* Registering your environments as ZenML stacks also enables you to browse and explore them in a convenient user interface. Try it out at [https://www.zenml.io/live-demo](https://www.zenml.io/live-demo)!
* **No Vendor Lock-In:** Since infrastructure is decoupled from code, ZenML gives you the freedom to switch to a different tooling stack whenever it suits you. By avoiding vendor lock-in, you have the flexibility to transition between cloud providers or services, ensuring that you receive the best performance and pricing available in the market at any time.

```Bash
zenml stack set gcp
python run.py  # Run your ML workflows in GCP
zenml stack set aws
python run.py  # Now your ML workflow runs in AWS
```

<Icon icon="rocket"/> **Learn More**

Ready to deploy and manage your MLOps infrastructure with ZenML? Here is a collection of pages you can take a look at next:

<CardGroup cols={3}>
 <Card title="Switch to production" icon="building" href="/user-guide/guides/production-guide/cloud-orchestration">
  Set up and manage production-ready infrastructure with ZenML.
</Card>
<Card title="Component guide" icon="list-check" href="/stack-components/component-guide">
 Explore the existing infrastructure and tooling integrations of ZenML.
</Card>
<Card title="FAQ" icon="person-circle-question" href="/getting-started/faq">
Find answers to the most frequently asked questions.
 </Card>
  </CardGroup>
  </Tab>
  <Tab title="For Data Scientists">
ZenML gives data scientists the freedom to fully focus on modeling and experimentation while writing code that is production-ready from the get-go.

* **Develop Locally:** ZenML allows you to develop ML models in any environment using your favorite tools. This means you can start developing locally, and simply switch to a production environment once you are satisfied with your results.

```py
python run.py  # develop your code locally with all your favorite tools
zenml stack set production
python run.py  # run on production infrastructure without any code changes
```
* **Pythonic SDK:** ZenML is designed to be as unintrusive as possible. Adding a ZenML `@step` or `@pipeline` decorator to your Python functions is enough to turn your existing code into ZenML pipelines:

```py
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
* **Automatic Metadata Tracking:** ZenML automatically tracks the metadata of all your runs and saves all your datasets and models to disk and versions them. Using the ZenML dashboard, you can see detailed visualizations of all your experiments. Try it out at [https://www.zenml.io/live-demo](https://www.zenml.io/live-demo)!

ZenML integrates seamlessly with many popular open-source tools, so you can also combine ZenML with other popular experiment tracking tools like [Weights & Biases](/stack-components/experiment-trackers/wandb), [MLflow](/stack-components/experiment-trackers/mlflow), or [Neptune](/stack-components/experiment-trackers/neptune) for even better reproducibility.

<Icon icon="rocket"/> **Learn More**

Ready to develop production-ready code with ZenML? Here is a collection of pages you can take a look at next:
<CardGroup cols={3}>

<Card title="Core Concepts" icon="trowel-bricks" href="/getting-started/core-concepts">
Understand the core concepts behind ZenML.
</Card>

<Card title="Starter Guide" icon="egg" href="/user-guide/guides/starter-guide">
Get started with ZenML and learn how to build your first pipeline and stack.
</Card>

<Card title="Quickstart (in Colab)" icon="person-running" href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb">
Build your first ZenML pipeline and deploy it in the cloud.
</Card>

</CardGroup>
  </Tab>
  <Tab title="For ML Engineers">
ZenML empowers ML engineers to take ownership of the entire ML lifecycle end-to-end. Adopting ZenML means fewer handover points and more visibility on what is happening in your organization.

* **ML Lifecycle Management:** ZenML's abstractions enable you to manage sophisticated ML setups with ease. After you define your ML workflows as [Pipelines](/getting-started/core-concepts#1-development) and your development, staging, and production infrastructures as [Stacks](/getting-started/core-concepts#2-execution), you can move entire ML workflows to different environments in seconds.
```Bash
zenml stack set staging
python run.py  # test your workflows on staging infrastructure
zenml stack set production
python run.py  # run your workflows in production
```
* **Reproducibility:** ZenML enables you to painlessly reproduce previous results by automatically tracking and versioning all stacks, pipelines, artifacts, and source code. In the ZenML dashboard, you can get an overview of everything that has happened and drill down into detailed lineage visualizations. Try it out at [https://www.zenml.io/live-demo](https://www.zenml.io/live-demo)!

<Frame>
  <img src=".gitbook/assets/FDashboard.png"/>
</Frame>

* **Automated Deployments:** With ZenML, you no longer need to upload custom Docker images to the cloud whenever you want to deploy a new model to production. Simply define your ML workflow as a ZenML pipeline, let ZenML handle the containerization, and have your model automatically deployed to a highly scalable Kubernetes deployment service like [Seldon](/stack-components/model-deployers/seldon).

```Bash
from zenml.integrations.seldon.steps import seldon_model_deployer_step
from my_organization.steps import data_loader_step, model_trainer_step
@pipeline
def my_pipeline():
  data = data_loader_step()
  model = model_trainer_step(data)
  seldon_model_deployer_step(model)
```

<Icon icon="rocket"/> **Learn More**

Ready to manage your ML lifecycles end-to-end with ZenML? Here is a collection of pages you can take a look at next:

<CardGroup cols={3}>

<Card title="Starter Guide" icon="egg" href="/user-guide/guides/starter-guide">
Get started with ZenML and learn how to build your first pipeline and stack.
</Card>

<Card title="How To" icon="earlybirds" href="/usage/pipelines/build-pipelines/build-pipelines">
Discover advanced ZenML features like config management and containerization.
</Card>

<Card title="Examples" icon="person-chalkboard" href="https://github.com/zenml-io/zenml-projects">
Explore ZenML through practical use-case examples.
</Card>

</CardGroup>
  </Tab>
</Tabs>






# Code Groups

Testing something here

<CodeGroup>

```javascript helloWorld.js
console.log("Hello World");
```

```python hello_world.py
print('Hello World!')
```

```java HelloWorld.java
class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

</CodeGroup>



# Steps

<Steps>
  <Step title="First Step">
    These are instructions or content that only pertain to the first step.
  </Step>
  <Step title="Second Step">
    These are instructions or content that only pertain to the second step.
  </Step>
  <Step title="Third Step">
    These are instructions or content that only pertain to the third step.
  </Step>
</Steps>


# Tabs

<Tabs>
  <Tab title="First Tab">
    ☝️ Welcome to the content that you can only see inside the first Tab.
  </Tab>
  <Tab title="Second Tab">
    ✌️ Here's content that's only inside the second Tab.
  </Tab>
  <Tab title="Third Tab">
    💪 Here's content that's only inside the third Tab.
  </Tab>
</Tabs>

