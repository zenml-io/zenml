---
description: A collection of architecture diagrams that shows the interactions of different environments in mature productions settings.
---

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


## Introducing a Secrets Manager
In most production settings it is preferred to store/rotate secrets within one
unified
[secret manager](secrets-managers/secrets-managers.md).
The client machines as well as the orchestration 
components (orchestrator/ step operator) can be separately authenticated with
this secret manager (e.g. with CLI authentication). Now the component 
configurations and docker images no longer rely on baked in credentials.

![Secret Manager](../assets/diagrams/Remote_with_secrets_manager.png) 


## The Experiment Tracker
The [experiment tracker](experiment-trackers/experiment-trackers.md) 
is a very popular component of the stack that helps log and compare the 
metrics of different runs. This diagram shows how the experiment tracker
fits into the overall architecture.

![Experiment Tracker](../assets/diagrams/Remote_with_exp_tracker.png) 

## The Model Deployer
At the end of a successful training pipeline, you might want to deploy your
models as prediction endpoints. This can be easily accomplished using
[model deployers](model-deployers/model-deployers.md).


![Model Deployer](../assets/diagrams/Remote_with_deployer.png) 