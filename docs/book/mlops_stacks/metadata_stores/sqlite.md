---
description: Store ML metadata on your local filesystem
---

The SQLite Metadata Store is a built-in ZenML [Metadata Store](./overview.md)
flavor that uses a SQLite database file on your local filesystem to store
ML metadata information.

## When would you want to use it?

The SQLite Metadata Store is a great way to get started with ZenML, as it doesn't
require you to provision additional local resources, or to deploy and manage
external database services, like a Kubeflow metadata service or a MySQL
database. All you need is the local filesystem. You should use the local
Metadata Store if you're just evaluating or getting started with ZenML, or if
you are still in the experimental phase and don't need to share your pipeline
run results with others.

{% hint style="warning" %}
The local Metadata Store is not meant to be utilized in production. The local
filesystem cannot be shared across your team and doesn't cover services like
high-availability, scalability, backup and restore and other features that are
expected from a production grade MLOps system.

The fact that it stores information on your local filesystem also means that not
all [Orchestrators](../orchestrators/overview.md) can be used in the same stack
as a local Metadata Store. Only Orchestrators running on the local machine, such
as the [local Orchestrator](../orchestrators/local.md), a [local Kubeflow Orchestrator](../orchestrators/kubeflow.md),
or a [local Kubernetes Orchestrator](../orchestrators/kubernetes.md) can be
combined with a local Metadata Store

As you transition to a team setting or a production setting, you can replace the
local Metadata Store in your stack with one of the other flavors that are
better suited for these purposes, with no changes required in your code.
{% endhint %}

## How do you deploy it?

The `default` stack that comes pre-configured with ZenML already contains a
SQLite Metadata Store:

```
$ zenml stack list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml metadata-store describe
Running without an active repository root.
Running with active profile: 'default' (global)
Running with active stack: 'default'
No component name given; using `default` from active stack.
                                    METADATA_STORE Component Configuration (ACTIVE)                                     
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ COMPONENT_PROPERTY        │ VALUE                                                                                    ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ TYPE                      │ metadata_store                                                                           ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ FLAVOR                    │ sqlite                                                                                   ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ NAME                      │ default                                                                                  ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                      │ 71bcbd88-6862-4e9a-8667-92539109a234                                                     ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ UPGRADE_MIGRATION_ENABLED │ True                                                                                     ┃
┠───────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┨
┃ URI                       │ /home/stefan/.config/zenml/local_stores/e76755ca-663d-4919-9a1b-c5ab919a8e0d/metadata.db ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

As shown by the `URI` value in the `zenml metadata-store describe` output, the
Metadata Store uses a database file on your local filesystem.

You can create additional instances of SQLite Metadata Stores and use them in
your stacks as you see fit, e.g.:

```shell
# Register the sqlite metadata store
zenml metadata-store register custom_sqlite --flavor sqlite

# Register and set a stack with the new metadata store
zenml stack register custom_stack -o default -a default -m custom_sqlite --set
```

{% hint style="warning" %}
The SQLite Metadata Store takes in a `uri` configuration parameter that can be
set during registration to point to a custom path on your machine. However, it
is highly recommended that you rely on the default `uri` value, otherwise it may
lead to unexpected results. Other local stack components depend on the
convention used for the default path to be able to access the local Metadata
Store.
{% endhint %}

For more, up-to-date information on the SQLite Metadata Store implementation and
its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.mysql_metadata_store).

## How do you use it?

Aside from the fact that the metadata information is stored locally, using the
SQLite Metadata Store is no different than [using any other flavor of Metadata Store](./overview.md#how-to-use-it).
