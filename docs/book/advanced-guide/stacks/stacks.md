---
description: How to leverage stacks
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The goal of this section is to showcase some critical advanced use-cases for
ZenML stacks.

## List of topics

* [Writing Custom Stack Component Flavors](./custom-flavors.md)
  can be useful when trying to use ZenML with tooling or infrastructure for
  which no official integration exists yet.
* [Managing Stack Component States](./stack-state-management.md)
  is required for certain integrations with remote components and can also be
  used to configure custom setup behavior of custom stack component flavors.
* [Managing External Services](./manage-external-services.md)
  might be required for deploying custom models or for the UI's of some
  visualization tools like TensorBoard. These services are usually long-lived
  external processes that persist beyond the execution of your pipeline runs.

{% hint style="info" %}
We will keep adding more use-cases to the advanced guide of ZenML stacks.
If there is a particular topic you can not find here or any use-case that
you would like learn more about, you can reach us in our
[Slack Channel](https://zenml.io/slack-invite).
{% endhint %}