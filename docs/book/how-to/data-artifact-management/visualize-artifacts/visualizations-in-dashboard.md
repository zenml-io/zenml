---
description: Displaying visualizations in the dashboard.
---

# Giving the ZenML Server Access to Visualizations

In order for the visualizations to show up on the dashboard, the following must be true:

## Configuring a Service Connector

Visualizations are usually stored alongside the artifact, in the [artifact store](../../../component-guide/artifact-stores/artifact-stores.md). Therefore, if a user would like to see the visualization displayed on the ZenML dashboard, they must give access to the server to connect to the artifact store.

The [service connector](../../infrastructure-deployment/auth-management/README.md) documentation goes deeper into the concept of service connectors and how they can be configured to give the server permission to access the artifact store. For a concrete example, see the [AWS S3](../../../component-guide/artifact-stores/s3.md) artifact store documentation.

{% hint style="info" %}
When using the default/local artifact store with a deployed ZenML, the server naturally does not have access to your local files. In this case, the visualizations are also not displayed on the dashboard.

Please use a service connector enabled and remote artifact store alongside a deployed ZenML to view visualizations.
{% endhint %}

## Configuring Artifact Stores

If all visualizations of a certain pipeline run are not showing up in the dashboard, it might be that your ZenML server does not have the required dependencies or permissions to access that artifact store. See the [custom artifact store docs page](../../../component-guide/artifact-stores/custom.md#enabling-artifact-visualizations-with-custom-artifact-stores) for more information.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
