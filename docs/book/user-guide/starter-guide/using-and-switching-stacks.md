---
description: How to use MLOps tools and infrastructure with stacks
---

# Understand your stack

<details>

<summary>Notes</summary>

* Shorter introduction?
* Link to all the different types of stack components here?
* I Propose the following flow -> Point to the line in the logs that mentions the default stack when running a pipeline -> explain what stacks are -> show where they live in the cli and on the dashboard ->&#x20;

</details>

### The stack

In the previous section you might have already noticed the term `stack` in the logs and on the dashboard.

A `stack` is the combination of tools and infrastructure that your pipelines can run on. In simple terms you could think of it as `environments` . Let's explore this.

{% tabs %}
{% tab title="CLI" %}
`zenml stack describe` lets you find out details about your active stack:

```bash
...
Running with active workspace: 'default' (global)
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
<figure><img src="../../.gitbook/assets/stack_in_dashboard.png" alt=""><figcaption></figcaption></figure>
{% endtab %}
{% endtabs %}

### Components of the Stack

As you can see in the section above, a stack consists of multiple components. All stacks have at minimum an **orchestrator** and an **artifact store**.&#x20;

The **orchestrator** is responsible for executing the pipeline code. In the simplest case, this will be a simple python thread on your machine. Let's explore this default orchestrator.

{% tabs %}
{% tab title="First Tab" %}

{% endtab %}

{% tab title="Second Tab" %}

{% endtab %}
{% endtabs %}

The **artifact store** is responsible for persisting the step outputs. As we learned in the previous section, the step outputs are not passed along in memory, rather the outputs of each step are stored in the **artifact store** and then loaded from there when the next step needs them. By default this will also be on your own machine:

{% tabs %}
{% tab title="First Tab" %}

{% endtab %}

{% tab title="Second Tab" %}

{% endtab %}
{% endtabs %}

...

...

...

## Stack

In ZenML, a **Stack** represents a set of configurations for your MLOps tools and infrastructure. For instance, you might want to:

* Orchestrate your ML workflows with [Kubeflow](broken-reference/),
* Save ML artifacts in an [Amazon S3](broken-reference/) bucket,
* Track your experiments with [Weights & Biases](broken-reference/),
* Deploy models on Kubernetes with [Seldon](broken-reference/) or [KServe](broken-reference/),

In the illustration, you see one user register two stacks, the `Local Stack` and a `Production Stack`. These stacks can be shared with other people easily - something we'll dig into more [later](broken-reference/).

![Running your pipeline in the cloud](../../assets/core\_concepts/03\_multi\_stack.png)

Any such combination of tools and infrastructure can be registered as a separate stack in ZenML. Since ZenML code is tooling-independent, you can switch between stacks with a single command and then automatically execute your ML workflows on the desired stack without having to modify your code.

## Stack Components

In ZenML, each MLOps tool is associated with a specific **Stack Component**, which is responsible for one specific task of your ML workflow. All stack components are grouped into [categories](broken-reference/).

For instance, each ZenML stack (e.g. the default stack above) includes an _Orchestrator_ which is responsible for the execution of the steps within your pipeline and an _Artifact Store_ which is responsible for storing the artifacts generated by your pipelines.

{% hint style="info" %}
Check out the [Categories of MLOps Tools](broken-reference/) page for a detailed overview of available stack components in ZenML.
{% endhint %}

### Orchestrator

The [Orchestrator](broken-reference/) is the component that defines how and where each pipeline step is executed when calling `pipeline.run()`. By [default](broken-reference/), all runs are executed locally, but by configuring a different orchestrator you can, e.g., automatically execute your ML workflows on [Kubeflow](broken-reference/) instead.

### Artifact Stores

Under the hood, all the artifacts in our ML pipeline are automatically stored in an [Artifact Store](broken-reference/). By [default](broken-reference/), this is simply a place in your local file system, but we could also configure ZenML to store this data in a cloud bucket like [Amazon S3](broken-reference/) or any other place instead.

You can see all supported stack component types in a single table view [here](broken-reference/)

{% hint style="info" %}
Every stack can usually contain one stack component category of each type, e.g., one `Orchestrator`, one `Artifact Store`, etc, but in some cases, you can have more than one stack component category in one stack (e.g. in the case of having two `Step Operators` in your stack). We will discuss this in later chapters.
{% endhint %}

## Stack Component Flavors

The specific tool you are using is called a **Flavor** of the stack component. E.g., _Kubeflow_ is a flavor of the _Orchestrator_ stack component category.

Out-of-the-box, ZenML already comes with a wide variety of flavors, which are either built-in or enabled through the installation of specific [Integrations](broken-reference/).

## Listing Stacks, Stack Components, and Flavors

{% hint style="info" %}
Our CLI features a wide variety of commands that let you manage and use your stacks. If you would like to learn more, please run: "`zenml stack --help`" or visit [our CLI docs](https://apidocs.zenml.io/latest/cli/).
{% endhint %}

You can see a list of all your _registered_ stacks with the following command:

```shell
zenml stack list
```

Similarly, you can see all _registered_ stack components of a specific type using `zenml <STACK_COMPONENT_CATEGORY> list`, e.g.:

```shell
zenml orchestrator list
```

In order to see all the _available_ flavors for a specific stack component use `zenml <STACK_COMPONENT_CATEGORY> flavor list`, e.g.:

```shell
zenml orchestrator flavor list
```

You can also see details of configuration parameters available for a flavor with `zenml <STACK_COMPONENT_CATEGORY> flavor describe <FLAVOR>`, e.g.:

```shell
zenml orchestrator flavor describe kubeflow
```

You can combine various MLOps tools into a ZenML stack as follows:

1. [Register a stack component](using-and-switching-stacks.md#registering-stack-components) to configure each tool using `zenml <STACK_COMPONENT> register`.
2. [Register a stack](using-and-switching-stacks.md#registering-a-stack) to bring a particular combination of stack components together using `zenml stack register`.
3. [Register a stack flavor](broken-reference/) to add a new tool to the ZenML flavor registry, if the tool you are looking for is not supported out-of-the-box, or if you want to modify standard behavior of standard flavors.

In this guide, we will learn about the first two, while the last is a slightly [advanced topic covered later](broken-reference/).

## Registering Stack Components

First, you need to create a new instance of the respective stack component with the desired flavor using `zenml <STACK_COMPONENT> register <NAME> --flavor=<FLAVOR>`. Most flavors require further parameters that you can pass as additional arguments `--param=value`, similar to how we passed the flavor.

E.g., to register a _local_ artifact store, we could use the following command:

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=local \
    --path=/path/to/your/store
```

In case you do not know all the available parameters, you can also use the interactive mode to register stack components. This will then walk you through each parameter (to skip just press ENTER):

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=local -i
```

Or you could simply describe the flavor to give a list of configuration available:

```shell
zenml artifact-store flavor describe local
```

After registering, you should be able to see the new artifact store in the list of registered artifact stores, which you can access using the following command:

```shell
zenml artifact-store list
```

Or you can register on the dashboard directly:

![Orchestrator list](broken-reference)

![Registering stack components](broken-reference)

{% hint style="info" %}
Our CLI features a wide variety of commands that let you manage and use your stack components and flavors. If you would like to learn more, please run `zenml <STACK_COMPONENT> --help` or visit [our CLI docs](https://apidocs.zenml.io/latest/cli/).
{% endhint %}

## Registering a Stack

After registering each tool as the respective stack components, you can combine all of them into one stack using the `zenml stack register` command:

```shell
zenml stack register <STACK_NAME> \
    --orchestrator <ORCHESTRATOR_NAME> \
    --artifact-store <ARTIFACT_STORE_NAME> \
    ...
```

{% hint style="info" %}
You can use `zenml stack register --help` to see a list of all possible arguments to the `zenml stack register` command, including a list of which option to use for which stack component.
{% endhint %}

Alternatively, you can see and register stacks on the dashboard as well:

![Stack list](broken-reference)

![Registering stack](broken-reference)

## Activating a Stack

Finally, to start using the stack you just registered, set it as active:

```shell
zenml stack set <STACK_NAME>
```

Now all your code is automatically executed using this stack.

## Changing Stacks

If you have multiple stacks configured, you can switch between them using the `zenml stack set` command, similar to how you [activate a stack](using-and-switching-stacks.md#activating-a-stack).

## Accessing the Active Stack in Python

The following code snippet shows how you can retrieve or modify information of your active stack and stack components in Python:

```python
from zenml.client import Client

client = Client()
active_stack = client.active_stack
print(active_stack.name)
print(active_stack.orchestrator.name)
print(active_stack.artifact_store.name)
print(active_stack.artifact_store.path)
```

## Unregistering Stacks

To unregister (delete) a stack and all of its components, run

```shell
zenml stack delete <STACK_NAME>
```

to delete the stack itself, followed by

```shell
zenml <STACK_COMPONENT> delete <STACK_COMPONENT_NAME>
```

to delete each of the individual stack components.

{% hint style="warning" %}
If you provisioned infrastructure related to the stack, make sure to deprovision it using `zenml stack down --force` before unregistering the stack. See the [Managing Stack States](broken-reference/) section for more details.
{% endhint %}
