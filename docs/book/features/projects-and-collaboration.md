---
description: Collaboration on ZenML Projects using the Zen Service.
---

# Service

The Zen Service provides a way to collaborate on ZenML projects by registering
stacks, project details, and tracking pipeline runs in a centralized location
over the network.

...

# Projects

The recommended way to start working on a ZenML project is to enter the folder
you wish to develop in and run `zenml init`. This command initializes a zen
repository by creating a `.zen` folder that keeps track which
[Profile](profiles.md) and which [Stack](../introduction/core-concepts.md#stack)
the project uses. If you are collaborating on the same project on multiple
machines using a centralized service, you may want to register this repository
with the service, so that the service is aware everybody is working on the same
project:

```shell
zenml project register $my-new-project
```

Alternatively, configure the repository to point to an existing project from the
service:

```shell
zenml project set $their-existing-project
```

Configuring a project in this way provides a convenient envelope to group
together pipelines and pipeline runs that belong to the same venture, even
though there may be multiple pipelines in that scope which also change over
time.

## Accessing Projects

To show all projects registered to your ZenStore/Service (optionally filtering
by creator) simply run:

```shell
zenml project list [--user=sam]
```

