---
description: Find answers to the most frequently asked questions about ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# ❓ FAQ

#### Why did you build ZenML?

We built it because we scratched our own itch while deploying multiple machine-learning models in production over the past three years. Our team struggled to find a simple yet production-ready solution whilst developing large-scale ML pipelines. We built a solution for it that we are now proud to share with all of you! Read more about this backstory [on our blog here](https://blog.zenml.io/why-zenml/).

#### Is ZenML just another orchestrator like Airflow, Kubeflow, Flyte, etc?

Not really! An orchestrator in MLOps is the system component that is responsible for executing and managing the execution of an ML pipeline. ZenML is a framework that allows you to run your pipelines on whatever orchestrator you like, and we coordinate with all the other parts of an ML system in production. There are [standard orchestrators](../component-guide/orchestrators/orchestrators.md) that ZenML supports out-of-the-box, but you are encouraged to [write your own orchestrator](../component-guide/orchestrators/custom.md) in order to gain more control as to exactly how your pipelines are executed!

#### Can I use the tool `X`? How does the tool `Y` integrate with ZenML?

Take a look at our [documentation](https://docs.zenml.io) (in particular the [component guide](../component-guide/README.md)), which contains instructions and sample code to support each integration that ZenML supports out-of-the-box. You can also check out [our integration test code](https://github.com/zenml-io/zenml/tree/main/tests/integration/examples) to see active examples of many of our integrations in action.

The ZenML team and community are constantly working to include more tools and integrations to the above list (check out the [roadmap](https://zenml.io/roadmap) for more details). You can [upvote features](https://zenml.io/discussion) you'd like and add your ideas to the roadmap.

Most importantly, ZenML is extensible, and we encourage you to use it with whatever other tools you require as part of your ML process and system(s). Check out [our documentation on how to get started](../introduction.md) with extending ZenML to learn more!

#### How can I make ZenML work with my custom tool? How can I extend or build on ZenML?

This depends on the tool and its respective MLOps category. We have a full guide on this over [here](../how-to/stack-deployment/implement-a-custom-stack-component.md)!

#### How can I contribute?

We develop ZenML together with our community! To get involved, the best way to get started is to select any issue from the [`good-first-issue` label](https://github.com/zenml-io/zenml/labels/good%20first%20issue). If you would like to contribute, please review our [Contributing Guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) for all relevant details.

#### How can I speak with the community?

The first point of the call should be [our Slack group](https://zenml.io/slack/). Ask your questions about bugs or specific use cases and someone from the core team will respond.

#### Which license does ZenML use?

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](https://github.com/zenml-io/zenml/blob/main/LICENSE) in this repository. Any contribution made to this project will be licensed under the Apache License Version 2.0.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
