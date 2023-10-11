---
description: An overview of advanced ZenML use cases
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The previous sections on [Steps and Pipelines](../steps-pipelines/steps-and-pipelines.md)
and [Stacks, Profiles, Repositories](../stacks-profiles-repositories/stacks-profiles-repositories.md)
already cover most of the concepts you will need for developing ML workflows
with ZenML.

However, there are a few additional use cases that you might or might not
encounter throughout your journey, about which you can learn more here.

## List of Advanced Use Cases

* [Writing Custom Stack Component Flavors](./custom-flavors.md)
can be useful when trying to use ZenML with tooling or infrastructure for which
no official integration exists yet.
* [Secret references](./secret-references.md) allow you to securely configure
sensitive information required in certain stack components.
* [Managing Stack Component States](./stack-state-management.md)
is required for certain integrations with remote components and can also be
used to configure custom setup behavior of custom stack component flavors.
* [Passing Custom Data Types through Steps](./materializer.md)
via **Materializers** is required if one of your steps outputs a custom class
or other data types, for which materialization is not defined by ZenML itself.
* [Accessing the Active Stack within Steps](./step-fixtures.md)
via **Step Fixtures** can, for instance, be used to load the best performing
prior model to compare newly trained models against.
* [Accessing Global Info within Steps](./environment.md)
via the **Environment** can be useful to get system information, the Python
version, or the name of the current step, pipeline, and run.
* [Managing External Services](./manage-external-services.md)
might be required for deploying custom models or for the UI's of some visualization
tools like TensorBoard. These services are usually long-lived external
processes that persist beyond the execution of your pipeline runs.
* [Managing Docker Images](./docker.md)
is required for some remote orchestrators and step operators to run your 
pipeline code in an isolated and well-defined environment.
* [Setting Stacks and Profiles with Environment Variables](./stack-profile-environment-variables.md)
enables you to configure pipeline runs with environment variables instead of
the repository.
* [Migrating Legacy Stacks to ZenML Profiles](./migrating-legacy-stacks.md)
contains additional information for returning users that want to port their
ZenML stacks to the newest version.
* [Specifying Hardware Resources for Steps](./specify-step-resources.md) explains
how to specify hardware resources like memory or the amount of CPUs and GPUs that
a step requires to execute.
