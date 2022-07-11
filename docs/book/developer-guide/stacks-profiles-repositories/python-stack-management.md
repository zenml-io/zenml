---
description: What are stacks, profiles, and repositories in ZenML?
---

# Managing Stacks in Python

One of the main purposes of interacting with the
[Repository](stacks_profiles_repositories.md#repositories) in Python is to
access and manage your stacks programmatically.

## Accessing the Active Stack

The following code snippet shows how you can retrieve or modify information
of your active stack and stack components in Python:

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

## Registering and Changing Stacks

In the following we use the repository to register a new ZenML stack called
`local` and set it as the active stack of the repository:

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
