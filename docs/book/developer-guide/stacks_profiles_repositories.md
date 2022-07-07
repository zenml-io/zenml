---
description: What are stacks, profiles, and repositories in ZenML?
---

# Stacks, Profiles, Repositories

## Stacks

## Profiles

## Repositories

ZenML has two main locations where it stores information on the local machine.
These are the _Global Config_ 
(see [Global Configuration](../resources/global_config.md)) and the 
_Repository_. The latter is also referred to as the _.zen folder_.

The ZenML **Repository** related to a pipeline run is the folder that contains 
all the files needed to execute the run, such as the respective Python scripts
and modules where the pipeline is defined, or other associated files.
The repository plays a double role in ZenML:

* It is used by ZenML to identify which files must be copied into Docker images 
in order to execute pipeline steps remotely, e.g., when orchestrating pipelines
with [KubeFlow](../mlops_stacks/orchestrators/kubeflow.md).
* It defines the local active [Profile](#profiles) and active [Stack](#stacks)
that will be used when running pipelines from the repository root or one of its
sub-folders.

### Registering a Repository

You can register your current working directory as a ZenML
Repository by running `zenml init`, e.g.:

```shell
stefan@aspyre2:/tmp/zenml$ zenml init
ZenML repository initialized at /tmp/zenml.
```

This will create a `/tmp/zenml/.zen` directory, which contains a single
`config.yaml` file that stores the local settings:

```yaml
active_profile_name: default
active_stack_name: default
```

To unregister the repository, simply delete the `.zen` directory in the
respective location, e.g., via `rm -rf /tmp/zenml/.zen`.

{% hint style="info" %}
It is recommended to use the `zenml init` command to initialize a ZenML
_Repository_ in the same location of your custom Python source tree where you
would normally point PYTHONPATH, especially if your Python code relies on a
hierarchy of modules spread out across multiple sub-folders.

ZenML CLI commands and ZenML code will display a warning if they are not running
in the context of a ZenML _Repository_, e.g.:

```shell
stefan@aspyre2:/tmp$ zenml stack list
Unable to find ZenML repository in your current working directory (/tmp) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```
{% endhint %}

## Managing stacks in Python via the Repository

You can access your repository in Python using the `zenml.repository.Repository`
class:

```python
from zenml.repository import Repository


repo = Repository()
```

This allows you to access and manage your stack and stack components from
within Python:

### Accessing the Active Stack

The following code snippet shows how you can retrieve or modify information
of your stack and stack components in Python:

```python
from zenml.repository import Repository


repo = Repository()
active_stack = repo.active_stack
print(active_stack.name)
print(active_stack.orchestrator.name)
print(active_stack.artifact_store.name)
print(active_stack.artifact_store.path)
print(active_stack.metadata_store.name)
print(active_stack.metadata_store.uri)
```

### Registering and Changing Stacks

In the following we use the repository to register a new ZenML stack called
`local` and to set it as the active stack of the repository:

```python
from zenml.repository import Repository
from zenml.artifact_stores import LocalArtifactStore
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack


repo = Repository()

# Create a new orchestrator
orchestrator = LocalOrchestrator(name="local")

# Create a new metadata store
metadata_store = SQLiteMetadataStore(
    name="local",
    uri="/tmp/zenml/zenml.db",
)

# Create a new artifact store
artifact_store = LocalArtifactStore(
    name="local",
    path="/tmp/zenml/artifacts",
)

# Create a new stack with the new components
stack = Stack(
    name="local",
    orchestrator=orchestrator,
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)

# Register the new stack in the currently active profile
repo.register_stack(stack)

# Set the stack as the active stack of the repository
repo.activate_stack(stack.name)
```

To explore all possible operations that can be performed via the
`Repository`, please consult the API docs section on
[Repository](https://apidocs.zenml.io/latest/api_docs/repository/#zenml.repository.Repository).
