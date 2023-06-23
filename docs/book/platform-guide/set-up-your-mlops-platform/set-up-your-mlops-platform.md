---
description: Birds-eye view on the necessities of your MLOps platform.
---

# 🏗 Set up your MLOps platform

In order to establish your own MLOps platform with ZenML, you need to deploy a
few ingredients:

<figure><img src="../../.gitbook/assets/SystemArchitecture.png" alt=""><figcaption><p>System architecture with a deployment of ZenML along with a cloud stack</p></figcaption></figure>

## The ZenML server

The ZenML server exposes a RESTful API to the client and other consumers.

#### **MySQL** **Database**

The database will act as the central metadata store that tracks all pipeline
runs and all the configurations of the
stacks.

#### Secret Store

For a production setting, you should also set up a secret manager as a backend
for all the secrets that will be used to configure stacks.

{% hint style="info" %}
See the following section to learn about the different ways
of [deploying ZenML](deploy-zenml/deploy-zenml.md).
{% endhint %}

## Stacks and their components

#### Compute Infrastructure

The Compute infrastructure (e.g. Kubernetes or serverless alternatives) is the 
location where the pipeline code is executed.

* This will be used to run the pipeline code runs in production using the **orchestrator** 
and **step operator** stack.
  components
* Optionally, the same infrastructure can be used for the deployment of models
  using the **model deployer** stack component.

{% hint style="warning" %}
The **orchestrator** will need to have access to all the other stack components,
and an egress path to post to the ZenML Server.
{% endhint %}

#### Data Storage

The **orchestrator**/**step operator** will use this as the **artifact store**
where step outputs are persisted. You can also use the same infrastructure to host your data as data sources/data sinks.

#### Container Registry

This is where the docker images for all pipeline code is pushed. The **orchestrator** will consume docker images from here.

#### Other Tools

Deployments of all the other tools that you need (such as **experiment trackers**, **model registries**, 
and **feature stores**). Learn more about the options in
our [Component Guide](../../user-guide/component-guide/component-guide.md).

### Additional Tools

There are some additional tools that should be considered in the setup of the
MLOps Platform.

#### Image Builder

Optionally, you can configure an image builder service to build the docker
images centrally, rather than doing so on the
client machine.

#### Code Repository

Code Repositories can be configured within the ZenML deployment. With a code
repository configured the pipeline code no
longer needs to be baked into the docker images. Instead, the code is loaded at
runtime within the orchestrator.

{% hint style="info" %}
**Coming Soon: True Client-Server Architecture**

We are hard at work implementing a true client-server architecture where the
client no longer needs to have any access
to the individual stack components. In the meantime, we recommend using your
favorite CI/CD tool to enable using ZenML
without the need to configure direct access to stack components from the client
machines. Check our exemplary implementation of this 
[here](https://github.com/zenml-io/zenml-gitflow).
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
