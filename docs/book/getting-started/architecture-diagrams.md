---
description: A collection of architecture diagrams that shows the interactions of different environments in mature productions settings.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


In order to understand the interaction between ZenML clients, a ZenML Server and
other environments, we have compiled a collection of diagrams that highlight 
certain interactions.

## The Basics
The most basic production stack will contain an orchestrator, an artifact store
and a Container registry. The following diagram show how a pipeline is run in 
such a configuration. After fetching the necessary information from the ZenML 
Server (which orchestrator, which container registry), the user code is built 
into a docker image on the client side. It is then pushed to the container
registry. The ZenML client then kicks off the pipeline run on the orchestrator
side. The orchestrator pulls the image containing the user code then assembles
and launches the pipeline. The individual steps communicate with the ZenML 
Server, to fetch information on other components and to read and write metadata
pertaining to the current pipeline run (this includes the location of previous 
step outputs/ cached data).


![Remote Stack](../assets/diagrams/RemoteServer.png)


## Using Git Ops
In many production settings it is undesirable to have all developers accessing 
and running on the production environments. Instead, this is usually centralized
through the means of git ops. This same principle can be easily used for 
pipeline deployments using ZenML. [Here](https://github.com/zenml-io/zenml-gitflow)
is an example repository that shows how. The following architecture diagram
visualizes how a pipeline would be run through an automated action that is
triggered when new code is pushed to the main code repository.

![ZenML with Git Ops](../assets/diagrams/Remote_with_git_ops.png)


## Introducing a Secrets Manager
In most production settings it is preferred to store/rotate secrets within one
unified
[secret manager](../component-gallery/secrets-managers/secrets-managers.md).
The client machines as well as the orchestration 
components (orchestrator/ step operator) can be separately authenticated with
this secret manager (e.g. with CLI authentication). Now the component 
configurations and docker images no longer rely on baked in credentials.

![Secret Manager](../assets/diagrams/Remote_with_secrets_manager.png) 


## The Experiment Tracker
The [experiment tracker](../component-gallery/experiment-trackers/experiment-trackers.md) 
is a very popular component of the stack that helps log and compare the 
metrics of different runs. This diagram shows how the experiment tracker
fits into the overall architecture.

![Experiment Tracker](../assets/diagrams/Remote_with_exp_tracker.png) 


## The Model Deployer
At the end of a successful training pipeline, you might want to deploy your
models as prediction endpoints. This can be easily accomplished using
[model deployers](../component-gallery/model-deployers/model-deployers.md).

![Model Deployer](../assets/diagrams/Remote_with_deployer.png) 


## The Model Registry
The [model registry](../component-gallery/model-registry/model-registry.md)
is a component that helps you keep track of your models. It can be used to
keep track of the different versions of a model, as well as enabling you to
easily deploy your models as prediction endpoints. This diagram shows how
the model registry fits into the overall architecture.

![Model Registry](../assets/diagrams/Remote_with_model_registry.png)