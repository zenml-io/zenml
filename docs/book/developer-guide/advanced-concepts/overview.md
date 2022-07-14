---
description: What are materializers, services, step contexts, and step fixtures.
---

The previous sections on [Steps and Pipelines](../steps-pipelines/steps-and-pipelines.md)
and [Stacks, Profiles, Repositories](../stacks-profiles-repositories/stacks_profiles_repositories.md)
already cover most of the concepts you will need for developing ML workflows
with ZenML.

However, there are a few additional use cases that you might or might not
encounter throughout your journey, about which you can learn more here.

## List of Advanced Use Cases

* [Passing Custom Data Types through Steps](developer-guide/advanced-concepts/materializer.md)
via **Materializers** is required if one of your steps outputs a custom class
or other data types, for which materialization is not defined by ZenML itself.
* [Accessing the Active Stack within Steps](developer-guide/advanced-concepts/step-fixtures.md)
via **Step Fixtures** can, for instance, be used to load the best performing
prior model to compare newly trained models against.
* [Accessing Global Infos within Steps](developer-guide/advanced-concepts/environment.md)
via the **Environment** can be useful to get system information, the Python
version, or the name of the current step, pipeline, and run.
* [Managing External Services](developer-guide/advanced-concepts/manage-external-services.md)
might be required for deploying custom models or for the UIs of some visualization
tools like TensorBoard. These services are usually long-lived external
processes that persist beyond the execution of your pipeline runs.
* [Managing Docker Images](developer-guide/advanced-concepts/docker.md)
is required for some remote orchestrators and step operators to run your 
pipeline code in an isolated and well-defined environment.
