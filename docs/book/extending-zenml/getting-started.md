---
description: How to get started with extending ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


While you are working on an ML task, it is very likely that you will require 
a custom tailored solution. This might not only mean that you have to write 
custom code, but also custom components for your infrastructure.

That's exactly why we built ZenML in a way which is completely open to 
extension. You can simply use our base abstractions, create your own flavors 
and generate custom stack components.

If you would like to learn more about how to achieve this with a specific 
stack component, please check the links below:

| **Type of Stack Component**                 | **Description**                                                   |
|---------------------------------------------|-------------------------------------------------------------------|
| [Orchestrator](orchestrators.md)             | Orchestrating the runs of your pipeline                           |
| [Artifact Store](artifact-stores.md)         | Storage for the artifacts created by your pipelines               |
| [Metadata Store](metadata-stores.md)         | Tracking the execution of your pipelines/steps                    |
| [Container Registry](container-registries.md) | Store for your containers                                         |
| [Secrets Manager](secrets-managers.md)       | Centralized location for the storage of your secrets              |
| [Step Operator](step-operators.md)           | Execution of individual steps in specialized runtime environments |
| [Model Deployer](model-deployers.md)         | Services/platforms responsible for online model serving           |
| [Feature Store](feature-stores.md)           | Management of your data/features                                  |
| [Experiment Tracker](experiment-trackers.md) | Tracking your ML experiments                                      |
| [Alerter](alerters.md)                       | Sending alerts through specified channels                         |


{% hint style="info" %}
Keep in mind that ZenML is an open-source project. We appreciate and thrive on 
the contribution from our community. If you would like to contribute your 
custom implementations back our repository, you can find the guide on 
[GitHub](https://github.com/zenml-io/zenml/blob/develop/CONTRIBUTING.md).
{% endhint %}
