---
description: Learn how to switch the infrastructure backend of your code.
---

# Switch stacks locally

## Stack

In the previous section you might have already noticed the term `stack` in the logs and on the dashboard.

A `stack` is the combination of tools and infrastructure that your pipelines can run on. When you get started with ZenML this will be the default stack. Let's explore what this is.

{% tabs %}
{% tab title="CLI" %}
`zenml stack describe` lets you find out details about your active stack:

```bash
...
        Stack Configuration        
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ COMPONENT_TYPE │ COMPONENT_NAME ┃
┠────────────────┼────────────────┨
┃ ARTIFACT_STORE │ default        ┃
┠────────────────┼────────────────┨
┃ ORCHESTRATOR   │ default        ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
     'default' stack (ACTIVE)      
Stack 'default' with id '...' is owned by user default and is 'private'.
...
```

`zenml stack list` lets you see all stacks that are registered in your zenml deployment.

```bash
...
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ STACK ID  │ SHARED │ OWNER   │ ARTIFACT_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼───────────┼────────┼─────────┼────────────────┼──────────────┨
┃   👉   │ default    │ ...       │ ➖     │ default │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
...
```

{% hint style="info" %}
As you can see a stack can be active on your client. This simply means that any pipeline you run, will be using the active stack as its environment.
{% endhint %}
{% endtab %}

{% tab title="Dashboard" %}
You can explore all your stacks in the dashboard. When you click on a specific one you can see its configuration and all the pipeline runs that were executed using this stack.

<figure><img src="../../.gitbook/assets/stack_in_dashboard.png" alt=""><figcaption><p>The default stack on the Dashboard</p></figcaption></figure>
{% endtab %}
{% endtabs %}

## Components of the Stack

As you can see in the section above, a stack consists of multiple components. All stacks have at minimum an **orchestrator** and an **artifact store**.

#### Orchestrator

The **orchestrator** is responsible for executing the pipeline code. In the simplest case, this will be a simple python thread on your machine. Let's explore this default orchestrator.

{% tabs %}
{% tab title="CLI" %}
`zenml orchestrator list` lets you see all orchestrators that are registered in your zenml deployment.

```bash
┏━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┓
┃ ACTIVE │ NAME    │ COMPONENT ID │ FLAVOR │ SHARED │ OWNER   ┃
┠────────┼─────────┼──────────────┼────────┼────────┼─────────┨
┃   👉   │ default │ ...          │ local  │ ➖     │ default ┃
┗━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┛
```
{% endtab %}
{% endtabs %}

#### Artifact Store

The **artifact store** is responsible for persisting the step outputs. As we learned in the previous section, the step outputs are not passed along in memory, rather the outputs of each step are stored in the **artifact store** and then loaded from there when the next step needs them. By default this will also be on your own machine:

{% tabs %}
{% tab title="CLI" %}
`zenml artifact-store list` lets you see all artifact stores that are registered in your zenml deployment.

```bash
┏━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┓
┃ ACTIVE │ NAME    │ COMPONENT ID │ FLAVOR │ SHARED │ OWNER   ┃
┠────────┼─────────┼──────────────┼────────┼────────┼─────────┨
┃   👉   │ default │ ...          │ local  │ ➖     │ default ┃
┗━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┛
```
{% endtab %}
{% endtabs %}

There are many more components that you can add to your stacks, like experiment trackers, model deployers. You can see all supported stack component types in a single table view [here](broken-reference/)

## Separating Code from Configuration and Infrastructure

<figure><img src="../../.gitbook/assets/02_pipeline_local_stack.png" alt=""><figcaption><p>ZenML is the translation layer that allows your code to run on any of your stacks</p></figcaption></figure>

As visualized in the diagram above, There are two domains that are combined through ZenML. The right side shows the code domain. The users python code is turned into a ZenML pipeline. On the left side you can see the infrastructure domain, in this case the default stack that you learned about above. By keeping these two domains separate, it is now easy to switch what stack your pipeline runs on without making any changes in the code.

## Create your first stack

### Create a different Artifact Store

{% tabs %}
{% tab title="CLI" %}
```bash
zenml artifact-store register --flavor=local my_artifact_store
```

Let'd decompose the command:

* `artifact-store` this describes the top level group, to find other stack components simply run `zenml --help`&#x20;
* `register` here we want to register a new component, instead we could also `update` , `delete`&#x20;
{% endtab %}

{% tab title="Second Tab" %}

{% endtab %}
{% endtabs %}





Before we can move on to using a cloud stack, we need to find out more about the ZenML server in the next section.

###
