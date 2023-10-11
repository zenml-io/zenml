---
description: How to link stacks to code with repositories
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


ZenML has two main locations where it stores information on the local machine.
These are the [Global Configuration](../../resources/global-config.md) and the 
_Repository_. The latter is also referred to as the _.zen folder_.

The ZenML **Repository** related to a pipeline run is the folder that contains 
all the files needed to execute the run, such as the respective Python scripts
and modules where the pipeline is defined, or other associated files.
The repository plays a double role in ZenML:

* It is used by ZenML to identify which files must be copied into Docker images 
in order to execute pipeline steps remotely, e.g., when orchestrating pipelines
with [Kubeflow](../../mlops-stacks/orchestrators/kubeflow.md).
* It defines the local active [Stack](#stacks) that will be used when running
pipelines from the repository root or one of its sub-folders, as shown
[below](#setting-the-local-active-stack).

## Registering a Repository

You can register your current working directory as a ZenML
repository by running:

```bash
zenml init
```

This will create a `.zen` directory, which contains a single
`config.yaml` file that stores the local settings:

```yaml
active_project_name: null
active_stack_name: default
```

{% hint style="info" %}
It is recommended to use the `zenml init` command to initialize a ZenML
_Repository_ in the same location of your custom Python source tree where you
would normally point `PYTHONPATH`, especially if your Python code relies on a
hierarchy of modules spread out across multiple sub-folders.

ZenML CLI commands and ZenML code will display a warning if they are not running
in the context of a ZenML repository, e.g.:

```shell
stefan@aspyre2:/tmp$ zenml stack list
Unable to find ZenML repository in your current working directory (/tmp) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```
{% endhint %}

## Setting the Local Active Stack

One of the most useful features of repositories is that you can configure a
different active stack for each of your projects. This is great if
you want to use ZenML for multiple projects on the same machine. Whenever you
create a new ML project, we recommend you run `zenml init` to create a separate
repository, then use it to define your stacks:

```bash
zenml init
zenml stack register ...
zenml stack set ...
```

If you do this, the correct stack will automatically get activated
whenever you change directory from one project to another in your terminal.

{% hint style="info" %}
Note that the stacks and stack components are still stored globally, even when
running from inside a ZenML repository. It is only the active stack setting
that can be configured locally.
{% endhint %}

### Detailed Example

<details>
<summary>Detailed usage example of local stacks</summary>

The following example shows how the active stack can be configured locally for a
project without impacting the global settings:

```
/tmp/zenml$ zenml stack list
Unable to find ZenML repository in your current working directory (/tmp/zenml)
or any parent directories. If you want to use an existing repository which is in
a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If
you want to create a new repository, run zenml init.
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ zenml      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml init
ZenML repository initialized at /tmp/zenml.
The local active stack was initialized to 'default'. This local configuration will
only take effect when you're running ZenML from the initialized repository root,
or from a subdirectory. For more information on repositories and configurations,
please visit https://docs.zenml.io/developer-guide/stacks-repositories.


$ zenml stack list
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ zenml      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml stack set zenml
Using the default local database.
Active repository stack set to: 'zenml'

/tmp/zenml$ zenml stack list
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ default    │ default        │ default        │ default      ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ zenml      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ cd ..
/tmp$ zenml stack list
Unable to find ZenML repository in your current working directory (/tmp) or any
parent directories. If you want to use an existing repository which is in a
different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you
want to create a new repository, run zenml init.
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ zenml      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

</details>

## Using the Repository in Python

You can access your repository in Python using the `zenml.repository.Repository`
class:

```python
from zenml.client import Client

client = Client()
```

This allows you to perform various repository operations directly in Python, 
such as [Inspecting Finished Pipeline Runs](../steps-pipelines/inspecting-pipeline-runs.md) or
accessing and managing stacks, as shown below.

{% hint style="info" %}
To explore all possible operations that can be performed via the
`Repository`, please consult the API docs section on
[Repository](https://apidocs.zenml.io/latest/api_docs/repository/#zenml.repository.Repository).
{% endhint %}

### Accessing the Active Stack

The following code snippet shows how you can retrieve or modify information
of your active stack and stack components in Python:

```python
from zenml.client import Client

client = Client()
active_stack = client.active_stack
print(active_stack.name)
print(active_stack.orchestrator.name)
print(active_stack.artifact_store.name)
print(active_stack.artifact_store.path)
print(active_stack.metadata_store.name)
print(active_stack.metadata_store.uri)
```

### Registering and Changing Stacks

In the following we use the repository to register a new ZenML stack called
`local` and set it as the active stack of the repository:

```python
from zenml.client import Client
from zenml.artifact_stores import LocalArtifactStore
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack

client = Client()

# Create a new orchestrator
orchestrator = LocalOrchestrator(name="local")

# Create a new artifact store
artifact_store = LocalArtifactStore(
    name="local",
    path="/tmp/zenml/artifacts",
)

# Create a new stack with the new components
stack = Stack(
    name="local",
    orchestrator=orchestrator,
    artifact_store=artifact_store,
)

# Register the new stack
client.register_stack(stack)

# Set the stack as the active stack of the repository
client.activate_stack(stack.name)
```

## Unregistering a Repository

To unregister a repository, delete the `.zen` directory in the
respective location, e.g., via 

```bash
rm -rf .zen
```