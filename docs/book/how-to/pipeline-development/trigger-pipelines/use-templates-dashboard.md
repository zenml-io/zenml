---
description: Create and run a template over the ZenML Dashboard
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


{% hint style="success" %}
This is a [ZenML Pro](https://zenml.io/pro)-only feature. Please
[sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

## Create a template

In order to create a template over the dashboard, go a pipeline run that you 
executed on a remote stack (i.e. at least a remote orchestrator, artifact 
store, and container registry):

![Create Templates on the dashboard](../../../.gitbook/assets/run-templates-create-1.png)

Click on `+ New Template`, give it a name and click `Create`:

![Template Details](../../../.gitbook/assets/run-templates-create-2.png)

## Run a template using the dashboard

In order to run a template from the dashboard:

- You can either click `Run a Pipeline` on the main `Pipelines` page, or
- You can go to a specific template page and click on `Run Template`.

Either way, you will be forwarded to a page where you will see the 
`Run Details`. Here, you have the option to upload a `.yaml` [configurations file](../../pipeline-development/use-configuration-files/README.md)
or change the configuration on the go by using our editor.

![Run Details](../../../.gitbook/assets/run-templates-run-1.png)

Once you run the template, a new run will be executed on the same stack as 
the original run was executed on.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
