---
icon: face-thinking
description: Links to common use cases, workflows and tasks using ZenML.
---

# How do I...?

**Last Updated**: December 13, 2023

Some common questions that we get asked are:

* **contribute** to ZenML's open-source codebase?

Please read [our Contribution guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) for more information. For small features and bug fixes, please open a pull request as described in the guide. For anything bigger, it is worth [posting a message in Slack](https://zenml.io/slack/) or [creating an issue](https://github.com/zenml-io/zenml/issues/new/choose) so we can best discuss and support your plans.

* **custom components**: adding them to ZenML?

Please start by [reading the general documentation page](../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md) on implementing a custom stack component which offers some general advice on what you'll need to do.

From there, each of the custom stack component types has a dedicated section about adding your own custom components. For example, for adding custom orchestrators you would [visit this page](../component-guide/orchestrators/custom.md).

* **dependency clashes** mitigation with ZenML?

Check out [our dedicated documentation page](../how-to/pipeline-development/configure-python-environments/handling-dependencies.md) on some ways you can try to solve these dependency and versioning issues.

* **deploy cloud infrastructure** and/or MLOps stacks?

ZenML is designed to be stack-agnostic, so you can use it with any cloud infrastructure or MLOps stack. Each of the documentation pages for stack components explain how to deploy these components on the most popular cloud providers.

* **deploy ZenML** on my internal company cluster?

Read [the documentation on self-hosted ZenML deployments](../getting-started/deploying-zenml/README.md) in which several options are presented.

* **hyperparameter tuning**?

[Our dedicated documentation guide](../how-to/pipeline-development/build-pipelines/hyper-parameter-tuning.md) on implementing this is the place to learn more.

* **reset** things when something goes wrong?

To reset your ZenML client, you can run `zenml clean` which will wipe your local metadata database and reset your client. Note that this is a destructive action, so feel free to [reach out to us on Slack](https://zenml.io/slack/) before doing this if you are unsure.

* **steps that create other steps AKA dynamic pipelines and steps**?

Please read our [general information on how to compose steps + pipelines together](../user-guide/starter-guide/create-an-ml-pipeline.md) to start with. You might also find the code examples in [our guide to implementing hyperparameter tuning](../how-to/pipeline-development/build-pipelines/hyper-parameter-tuning.md) which is related to this topic.

* **templates**: using starter code with ZenML?

[Project templates](../how-to/setting-up-a-project-repository/using-project-templates.md) allow you to get going quickly with ZenML. We recommend the Starter template (`starter`) for most use cases which gives you a basic scaffold and structure around which you can write your own code. You can also build templates for others inside a Git repository and use them with ZenML's templates functionality.

* **upgrade** my ZenML client and/or server?

Upgrading your ZenML client package is as simple as running `pip install --upgrade zenml` in your terminal. For upgrading your ZenML server, please refer to [the dedicated documentation section](../getting-started/deploying-zenml/manage-the-deployed-services/upgrade-the-version-of-the-zenml-server.md) which covers most of the ways you might do this as well as common troubleshooting steps.

* use a \<YOUR\_COMPONENT\_GOES\_HERE> stack component?

For information on how to use a specific stack component, please refer to [the component guide](../component-guide/README.md) which contains all our tips and advice on how to use each integration and component with ZenML.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
