---
description: Configure pipelines at will with ZenML.
---

The goal of this section is to showcase some critical advanced use-cases 
regarding the configuration of different ZenML resources.

## List of topics

* [Runtime Settings](./settings.md) showcases how to
configure different ZenML resource during the runtime of a pipeline.
* [Passing Custom Data Types through Steps](./materializers.md)
via **Materializers** is required if one of your steps outputs a custom class
or other data types, for which materialization is not defined by ZenML itself.
* [Specifying Hardware Resources for Steps](./step-resources.md) explains
how to specify hardware resources like memory or the amount of CPUs and GPUs that
a step requires to execute.
* [Enabling GPU-backed hardware](./gpu-hardware.md) goes through best practices of
running in remote settings with a GPU attached.
* [Scheduling Pipeline Runs](./scheduling-runs.md) describes how to deploy pipelines
to run on a schedule.
* [Access metadata within steps](./step-metadata.md)
via **Step Fixtures** can, for instance, be used to load the best performing
prior model to compare newly trained models against.
* [Controlling the Step Execution Order](./step-order.md) explains how
to control the order in which steps of a pipeline get executed.

{% hint style="info" %}
We will keep adding more use-cases to the advanced guide of ZenML.
If there is a particular topic you cannot find here or any use-case that
you would like learn more about, you can reach us in our
[Slack Channel](https://zenml.io/slack-invite).
{% endhint %}