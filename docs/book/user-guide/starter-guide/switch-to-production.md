---
description: Bringing your pipelines into production using ZenML Sandbox
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Switch to production

Transitioning your machine learning pipelines to production means deploying your models on real-world data to make
predictions that drive business decisions. To achieve this, you need an infrastructure that can handle the demands of
running machine learning models at scale. However, setting up such an infrastructure involves careful planning and
consideration of various factors, such as data storage, compute resources, monitoring, and security.

Moving to a production environment offers several benefits over staying local:

1. **Scalability**: Production environments are designed to handle large-scale workloads, allowing your models to
   process more data and deliver faster results.
2. **Reliability**: Production-grade infrastructure ensures high availability and fault tolerance, minimizing downtime
   and ensuring consistent performance.
3. **Collaboration**: A shared production environment enables seamless collaboration between team members, making it
   easier to iterate on models and share insights.

Despite these advantages, transitioning to production can be challenging due to the complexities involved in setting up
the needed infrastructure.

This is where ZenML comes in. By providing seamless integration with
various [MLOps tools](/docs/book/user-guide/component-guide/integration-overview.md) and platforms, ZenML simplifies the
process of moving your pipelines into production. One way it does this is by offering a free, limited, and easy-to-use 
Sandbox environment that allows you to experiment with remote stacks without any setup or configuration.

For those who prefer more control over their infrastructure, ZenML offers a more manual approach that still streamlines
parts of the deployment process. With
the [deploy CLI](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-and-set-up-a-cloud-stack.md)
, you can quickly set up a full-fledged MLOps stack with just a few commands. You have the option to deploy individual
stack components through
the [stack-component CLI](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-component.md)
or [deploy a stack with multiple components](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-using-stack-recipes.md)
together using Terraform stack recipes.

### ZenML Sandbox: a simple and easy starting point

To help you get started with moving your pipelines into production, ZenML offers a managed Sandbox environment with a
pre-configured remote stack for users to try out its features without setting up their own infrastructure. The ZenML
Sandbox provides an isolated environment where you can experiment with different configurations and learn how to switch
between remote stacks.

### Getting started with ZenML Sandbox

#### Step 1: Sign up

To start using the ZenML Sandbox, sign up with your Google account. This will create a new sandbox environment for you
to explore ZenML and its features.

#### Step 2: Access credentials

After signing up and creating your sandbox, you will be provided with credentials
for [Kubeflow](/docs/book/user-guide/component-guide/orchestrators/kubeflow.md)
, [MinIO](../component-guide/artifact-stores/s3.md)
, [MLflow](/docs/book/user-guide/component-guide/experiment-trackers/mlflow.md),
and [ZenML Server](connect-to-a-deployed-zenml.md). These
credentials will allow you to access and interact with the various applications and services within the sandbox.

#### Step 3: Connect and set the stack

Use the `zenml connect` command to connect your local ZenML installation to the sandbox environment. Then, use
the `zenml stack set` command to set the appropriate stack for your sandbox.

```bash
zenml connect --url <sandbox_url> --username <username>
zenml stack set <stack_name>
```

#### Step 4: Explore pre-built pipelines

The ZenML Sandbox provides a repository of pre-built pipelines that users can choose from to run on their sandbox. Users
can access these pipelines through the ZenML Sandbox interface and run them using the provided credentials for Kubeflow,
MLflow, and ZenML.

#### Step 5: Run pipelines

To run a pipeline in the sandbox, use the `python run.py` command. You can either clone a repository with the pipelines
or use a special ZenML command to run them, to be decided.

```bash
python run.py
```

#### Step 6: Sandbox deletion

After 8 hours, your sandbox will be automatically deleted. Make sure to save any important data or results before the
sandbox is deleted. While the sandbox is active, you can also delete it manually through the ZenML Sandbox interface.

### ZenML Sandbox service status

The status of the ZenML Sandbox service is being tracked live in [the ZenML status page](https://zenml.statuspage.io/).
You can subscribe there to receive notifications about scheduled maintenance windows, unplanned downtime events and
more.

<figure><img src="../../.gitbook/assets/statuspage.png" alt=""><figcaption><p>The ZenML public services status page</p></figcaption></figure>

### Sandbox FAQ

**Q: Can I create more than one sandbox at a time?**

**A:** No, each user can create only one sandbox at a time. Once your current sandbox is deleted, you can create a new
one.

**Q: Can I extend the 8-hour limit for my sandbox?**

**A:** The 8-hour limit is fixed and cannot be extended. However, you can create a new sandbox after your current one is
deleted.

Q: **Can I use my own pipelines in the ZenML Sandbox?**

**A:** The ZenML Sandbox is designed for users to explore ZenML using pre-built example pipelines. While it is possible
to use your own pipelines, however, we do not recommend it as the sandbox is not designed for this purpose, since every
user is provided with limited resources.

**Q: Are there any model deployment options available in the ZenML Sandbox?**

**A:** At the moment, there are no model deployment tools available in the ZenML Sandbox. However, we are working on
adding this feature in the future.
