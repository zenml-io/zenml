---
description: Birds eye view on the necessities of your MLOps Platform
---

# 🏗 Set up your MLOps Platform

To set up your own MLOps Platform with ZenML you need the following ingredients:

* Deployment of the **ZenML Server** along with its **Database**
  * The database will act as the central metadata store that tracks all pipeline runs
  * The ZenML Server is the central point where all the runtime configuration of your architecture can be configured and shared
  * Optionally, you need to set up a **secret manager** as a secrets backend
* Compute infrastructure (e.g. Kubernetes or serverless alternatives)
  * This will be used to run the pipeline code runs in production using the **orchestrator** and **step operator** stack components
  * Optionally, this can also be used as the final location for models to be deployed to using the **model deployer** stack component
* A data storage solution where step outputs are persisted (e.g. S3)
  * This will be used as **artifact store** by the orchestrator
  * You can also use this as data sources/ data sinks
* A **container registry**
  * This is where the docker images for all pipeline code is pushed
  * The orchestrator will consume docker images from here
* Deployments of all the other tools that you need (such as **experiment trackers**, **model registries**, **feature stores**)&#x20;
