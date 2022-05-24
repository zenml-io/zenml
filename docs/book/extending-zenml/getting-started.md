---
description: How to get started with extending ZenML.
---

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
| [Orchestrator](orchestrator.md)             | Orchestrating the runs of your pipeline                           |
| [Artifact Store](artifact-store.md)         | Storage for the artifacts created by your pipelines               |
| [Metadata Store](metadata-store.md)         | Tracking the execution of your pipelines/steps                    |
| [Container Registry](container-registry.md) | Store for your containers                                         |
| [Secrets Manager](secrets-manager.md)       | Centralized location for the storage of your secrets              |
| [Step Operator](step-operator.md)           | Execution of individual steps in specialized runtime environments |
| [Model Deployer](model-deployer.md)         | Services/platforms responsible for online model serving           |
| [Feature Store](feature-store.md)           | Management of your data/features                                  |
| [Experiment Tracker](experiment-tracker.md) | Tracking your ML experiments                                      |
| [Alerter](alerter.md)                       | Sending alerts through specified channels                         |


{% hint style="info" %}
Keep in mind that ZenML is an open-source project. We appreciate and thrive on 
the contribution from our community. If you would like to contribute your 
custom implementations back our repository, you can find the guide on 
[GitHub](https://github.com/zenml-io/zenml/blob/develop/CONTRIBUTING.md).
{% endhint %}
