---
description: Find answers to the most frequently asked questions about ZenML.
icon: circle-question
---

# FAQ

This page addresses common questions about ZenML, including general information about the project and how to accomplish specific tasks.

## About ZenML

#### Why did you build ZenML?

We built it because we scratched our own itch while deploying multiple machine-learning models in production over the past three years. Our team struggled to find a simple yet production-ready solution whilst developing large-scale ML pipelines. We built a solution for it that we are now proud to share with all of you! Read more about this backstory [on our blog here](https://blog.zenml.io/why-zenml/).

#### Is ZenML just another orchestrator like Airflow, Kubeflow, Flyte, etc?

Not really! An orchestrator in MLOps is the system component that is responsible for executing and managing the execution of an ML pipeline. ZenML is a framework that allows you to run your pipelines on whatever orchestrator you like, and we coordinate with all the other parts of an ML system in production. There are [standard orchestrators](https://docs.zenml.io/stacks/orchestrators) that ZenML supports out-of-the-box, but you are encouraged to [write your own orchestrator](https://docs.zenml.io/stacks/orchestrators/custom) in order to gain more control as to exactly how your pipelines are executed!

#### Can I use the tool `X`? How does the tool `Y` integrate with ZenML?

Take a look at our [documentation](https://docs.zenml.io) (in particular the [component guide](https://docs.zenml.io/stacks)), which contains instructions and sample code to support each integration that ZenML supports out of the box. You can also check out [our integration test code](https://github.com/zenml-io/zenml/tree/main/tests/integration/examples) to see active examples of many of our integrations in action.

The ZenML team and community are constantly working to include more tools and integrations to the above list (check out the [roadmap](https://zenml.io/roadmap) for more details). 

Most importantly, ZenML is extensible, and we encourage you to use it with whatever other tools you require as part of your ML process and system(s). Check out [our documentation on how to get started](../introduction.md) with extending ZenML to learn more!

#### Which license does ZenML use?

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](https://github.com/zenml-io/zenml/blob/main/LICENSE) in this repository. Any contribution made to this project will be licensed under the Apache License Version 2.0.

## Platform Support

#### Do you support Windows?

ZenML officially supports Windows if you're using WSL. Much of ZenML will also work on Windows outside a WSL environment, but we don't officially support it, and some features don't work (notably anything that requires spinning up a server process).

#### Do you support Macs running on Apple Silicon?

Yes, ZenML does support Macs running on Apple Silicon. You just need to make sure that you set the following environment variable:

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

This is a known issue with how forking works on Macs running on Apple Silicon, and it will enable you to use ZenML and the server. This environment variable is needed if you are working with a local server on your Mac, but if you're just using ZenML as a client / CLI and connecting to a deployed server, then you don't need to set it.

## Common Use Cases and How-To's

#### How do I contribute to ZenML's open-source codebase?

We develop ZenML together with our community! To get involved, the best way to get started is to select any issue from the [`good-first-issue` label](https://github.com/zenml-io/zenml/labels/good%20first%20issue).

Please read [our Contribution Guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) for more information. For small features and bug fixes, please open a pull request as described in the guide. For anything bigger, it is worth [posting a message in Slack](https://zenml.io/slack/) or [creating an issue](https://github.com/zenml-io/zenml/issues/new/choose) so we can best discuss and support your plans.

#### How do I add custom components to ZenML?

Please start by [reading the general documentation page](https://docs.zenml.io/stacks/contribute/custom-stack-component) on implementing a custom stack component, which offers some general advice on what you'll need to do.

From there, each of the custom stack component types has a dedicated section about adding your own custom components. For example, to add a custom orchestrator, you would [visit this page](https://docs.zenml.io/stacks/orchestrators/custom).

#### How do I mitigate dependency clashes with ZenML?

Check out [our dedicated documentation page](https://docs.zenml.io/user-guides/best-practices/configure-python-environments) on some ways you can try to solve these dependency and versioning issues.

#### How do I deploy cloud infrastructure and/or MLOps stacks?

ZenML is designed to be stack-agnostic, so you can use it with any cloud infrastructure or MLOps stack. Each of the documentation pages for stack components explain how to deploy these components on the most popular cloud providers.

#### How do I deploy ZenML on my internal company cluster?

Read [the documentation on self-hosted ZenML deployments](../getting-started/deploying-zenml/), in which several options are presented.

#### How do I implement hyperparameter tuning?

[Our dedicated documentation guide](../user-guide/tutorial/hyper-parameter-tuning.md) on implementing this is the place to learn more.

#### How do I reset things when something goes wrong?

To reset your ZenML client, you can run `zenml clean` which will wipe your local metadata database and reset your client. Note that this is a destructive action, so feel free to [reach out to us on Slack](https://zenml.io/slack/) before doing this if you are unsure.

#### How do I create dynamic pipelines and steps?

Please read our [general information on how to compose steps + pipelines together](https://docs.zenml.io/user-guides/starter-guide/create-an-ml-pipeline) to start with. You might also find the code examples in [our guide to implementing hyperparameter tuning](https://docs.zenml.io/user-guides/tutorial/hyper-parameter-tuning) which is related to this topic.

#### How do I use templates and starter code with ZenML?

[Project templates](https://docs.zenml.io/user-guides/best-practices/project-templates) allow you to get going quickly with ZenML. We recommend the Starter template (`starter`) for most use cases, which gives you a basic scaffold and structure around which you can write your own code. You can also build templates for others inside a Git repository and use them with ZenML's templates functionality.

#### How do I upgrade my ZenML client and/or server?

Upgrading your ZenML client package is as simple as running `pip install --upgrade zenml` in your terminal. For upgrading your ZenML server, please refer to [the dedicated documentation section](../how-to/manage-zenml-server/upgrade-zenml-server.md), which covers most of the ways you might do this as well as common troubleshooting steps.

#### How do I use a specific stack component?

For information on how to use a specific stack component, please refer to [the component guide](https://docs.zenml.io/stacks), which contains all our tips and advice on how to use each integration and component with ZenML.

## Community and Support

#### How can I speak with the community?

The first point of contact should be [our Slack group](https://zenml.io/slack/). Ask your questions about bugs or specific use cases, and someone from the core team will respond.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
