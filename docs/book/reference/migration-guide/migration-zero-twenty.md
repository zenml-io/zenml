---
description: How to migrate from ZenML <=0.13.2 to 0.20.0.
---

# Migration guide 0.13.2 → 0.20.0

*Last updated: 2023-07-24*

The ZenML 0.20.0 release brings a number of big changes to its architecture and its features, some of which are not backwards compatible with previous versions. This guide walks you through these changes and offers instructions on how to migrate your existing ZenML stacks and pipelines to the new version with minimal effort and disruption to your existing workloads.

{% hint style="warning" %}
Updating to ZenML 0.20.0 needs to be followed by a migration of your existing ZenML Stacks and you may also need to make changes to your current ZenML pipeline code. Please read this guide carefully and follow the migration instructions to ensure a smooth transition.

If you have updated to ZenML 0.20.0 by mistake or are experiencing issues with the new version, you can always go back to the previous version by using `pip install zenml==0.13.2` instead of `pip install zenml` when installing ZenML manually or in your scripts.
{% endhint %}

High-level overview of the changes:

* [ZenML takes over the Metadata Store](migration-zero-twenty.md#zenml-takes-over-the-metadata-store-role) role. All information about your ZenML Stacks, pipelines, and artifacts is now tracked by ZenML itself directly. If you are currently using remote Metadata Stores (e.g. deployed in cloud) in your stacks, you will probably need to replace them with [ZenML cloud deployments](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md).
* the [new ZenML Dashboard](migration-zero-twenty.md#the-zenml-dashboard-is-now-available) is now available with all ZenML deployments.
* [ZenML Profiles have been removed](migration-zero-twenty.md#removal-of-profiles-and-the-local-yaml-database) in favor of ZenML Projects. You need to [manually migrate your existing ZenML Profiles](migration-zero-twenty.md#-how-to-migrate-your-profiles) after the update.
* the [configuration of Stack Components is now decoupled from their implementation](migration-zero-twenty.md#decoupling-stack-component-configuration-from-implementation). If you extended ZenML with custom stack component implementations, you may need to update the way they are registered in ZenML.
* the updated ZenML server provides a new and improved collaborative experience. When connected to a ZenML server, you can now [share your ZenML Stacks and Stack Components](migration-zero-twenty.md#shared-zenml-stacks-and-stack-components) with other users. If you were previously using the ZenML Profiles or the ZenML server to share your ZenML Stacks, you should switch to the new ZenML server and Dashboard and update your existing workflows to reflect the new features.

## ZenML takes over the Metadata Store role

ZenML can now run [as a server](../../user-guide/getting-started/core-concepts.md#zenml-server-and-dashboard) that can be accessed via a REST API and also comes with a visual user interface (called the ZenML Dashboard). This server can be deployed in arbitrary environments (local, on-prem, via Docker, on AWS, GCP, Azure etc.) and supports user management, workspace scoping, and more.

The release introduces a series of commands to facilitate managing the lifecycle of the ZenML server and to access the pipeline and pipeline run information:

* `zenml connect / disconnect / down / up / logs / status` can be used to configure your client to connect to a ZenML server, to start a local ZenML Dashboard or to deploy a ZenML server to a cloud environment. For more information on how to use these commands, see [the ZenML deployment documentation](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md).
* `zenml pipeline list / runs / delete` can be used to display information and about and manage your pipelines and pipeline runs.

In ZenML 0.13.2 and earlier versions, information about pipelines and pipeline runs used to be stored in a separate stack component called the Metadata Store. Starting with 0.20.0, the role of the Metadata Store is now taken over by ZenML itself. This means that the Metadata Store is no longer a separate component in the ZenML architecture, but rather a part of the ZenML core, located wherever ZenML is deployed: locally on your machine or running remotely as a server.

All metadata is now stored, tracked, and managed by ZenML itself. The Metadata Store stack component type and all its implementations have been deprecated and removed. It is no longer possible to register them or include them in ZenML stacks. This is a key architectural change in ZenML 0.20.0 that further improves usability, reproducibility and makes it possible to visualize and manage all your pipelines and pipeline runs in the new ZenML Dashboard.

The architecture changes for the local case are shown in the diagram below:

![ZenML local metadata before 0.20.0](../../user-guide/assets/migration/local-metadata-pre-0.20.png) ![ZenML local metadata after 0.20.0](../../user-guide/assets/migration/local-metadata-post-0.20.png)

The architecture changes for the remote case are shown in the diagram below:

![ZenML remote metadata before 0.20.0](../../user-guide/assets/migration/remote-metadata-pre-0.20.png) ![ZenML remote metadata after 0.20.0](../../user-guide/assets/migration/remote-metadata-post-0.20.png)

If you're already using ZenML, aside from the above limitation, this change will impact you differently, depending on the flavor of Metadata Stores you have in your stacks:

* if you're using the default `sqlite` Metadata Store flavor in your stacks, you don't need to do anything. ZenML will automatically switch to using its local database instead of your `sqlite` Metadata Stores when you update to 0.20.0 (also see how to [migrate your stacks](migration-zero-twenty.md#-how-to-migrate-your-profiles)).
* if you're using the `kubeflow` Metadata Store flavor _only as a way to connect to the local Kubeflow Metadata Service_ (i.e. the one installed by the `kubeflow` Orchestrator in a local k3d Kubernetes cluster), you also don't need to do anything explicitly. When you [migrate your stacks](migration-zero-twenty.md#-how-to-migrate-your-profiles) to ZenML 0.20.0, ZenML will automatically switch to using its local database.
* if you're using the `kubeflow` Metadata Store flavor to connect to a remote Kubeflow Metadata Service such as those provided by a Kubeflow installation running in AWS, Google or Azure, there is currently no equivalent in ZenML 0.20.0. You'll need to [deploy a ZenML Server](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md) instance close to where your Kubeflow service is running (e.g. in the same cloud region).
* if you're using the `mysql` Metadata Store flavor to connect to a remote MySQL database service (e.g. a managed AWS, GCP or Azure MySQL service), you'll have to [deploy a ZenML Server](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md) instance connected to that same database.
* if you deployed a `kubernetes` Metadata Store flavor (i.e. a MySQL database service deployed in Kubernetes), you can [deploy a ZenML Server](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md) in the same Kubernetes cluster and connect it to that same database. However, ZenML will no longer provide the `kubernetes` Metadata Store flavor and you'll have to manage the Kubernetes MySQL database service deployment yourself going forward.

{% hint style="info" %}
The ZenML Server inherits the same limitations that the Metadata Store had prior to ZenML 0.20.0:

* it is not possible to use a local ZenML Server to track pipelines and pipeline runs that are running remotely in the cloud, unless the ZenML server is explicitly configured to be reachable from the cloud (e.g. by using a public IP address or a VPN connection).
* using a remote ZenML Server to track pipelines and pipeline runs that are running locally is possible, but can have significant performance issues due to the network latency.

It is therefore recommended that you always use a ZenML deployment that is located as close as possible to and reachable from where your pipelines and step operators are running. This will ensure the best possible performance and usability.
{% endhint %}

### 👣 How to migrate pipeline runs from your old metadata stores

{% hint style="info" %}
The `zenml pipeline runs migrate` CLI command is only available under ZenML versions \[0.21.0, 0.21.1, 0.22.0]. If you want to migrate your existing ZenML runs from `zenml<0.20.0` to `zenml>0.22.0`, please first upgrade to `zenml==0.22.0` and migrate your runs as shown below, then upgrade to the newer version.
{% endhint %}

To migrate the pipeline run information already stored in an existing metadata store to the new ZenML paradigm, you can use the `zenml pipeline runs migrate` CLI command.

1. Before upgrading ZenML, make a backup of all metadata stores you want to migrate, then upgrade ZenML.
2. Decide the ZenML deployment model that you want to follow for your projects. See the [ZenML deployment documentation](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md) for available deployment scenarios. If you decide on using a local or remote ZenML server to manage your pipelines, make sure that you first connect your client to it by running `zenml connect`.
3. Use the `zenml pipeline runs migrate` CLI command to migrate your old pipeline runs:

* If you want to migrate from a local SQLite metadata store, you only need to pass the path to the metadata store to the command, e.g.:

```bash
zenml pipeline runs migrate PATH/TO/LOCAL/STORE/metadata.db
```

* If you would like to migrate any other store, you will need to set `--database_type=mysql` and provide the MySQL host, username, and password in addition to the database, e.g.:

```bash
zenml pipeline runs migrate DATABASE_NAME \
  --database_type=mysql \
  --mysql_host=URL/TO/MYSQL \
  --mysql_username=MYSQL_USERNAME \
  --mysql_password=MYSQL_PASSWORD
```

### 💾 The New Way (CLI Command Cheat Sheet)

**Deploy the server**

`zenml deploy --aws` (maybe don’t do this :) since it spins up infrastructure on AWS…)

**Spin up a local ZenML Server**

`zenml up`

**Connect to a pre-existing server**

`zenml connect` (pass in URL / etc, or zenml connect --config + yaml file)

**List your deployed server details**

`zenml status`

## The ZenML Dashboard is now available

The new ZenML Dashboard is now bundled into the ZenML Python package and can be launched directly from Python. The source code lives in the [ZenML Dashboard repository](https://github.com/zenml-io/zenml-dashboard).

To launch it locally, simply run `zenml up` on your machine and follow the instructions:

```bash
$ zenml up
Deploying a local ZenML server with name 'local'.
Connecting ZenML to the 'local' local ZenML server (http://127.0.0.1:8237).
Updated the global store configuration.
Connected ZenML to the 'local' local ZenML server (http://127.0.0.1:8237).
The local ZenML dashboard is available at 'http://127.0.0.1:8237'. You can
connect to it using the 'default' username and an empty password.
```

The Dashboard will be available at `http://localhost:8237` by default:

![ZenML Dashboard Preview](../../user-guide/assets/migration/zenml-dashboard.png)

For more details on other possible deployment options, see the [ZenML deployment documentation](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md), and/or follow the [starter guide](../../user-guide/starter-guide/pipelines/pipelines.md) to learn more.

## Removal of Profiles and the local YAML database

Prior to 0.20.0, ZenML used used a set of local YAML files to store information about the Stacks and Stack Components that were registered on your machine. In addition to that, these Stacks could be grouped together and organized under individual Profiles.

Profiles and the local YAML database have both been deprecated and removed in ZenML 0.20.0. Stack, Stack Components as well as all other information that ZenML tracks, such as Pipelines and Pipeline Runs, are now stored in a single SQL database. These entities are no longer organized into Profiles, but they can be scoped into different Projects instead.

{% hint style="warning" %}
Since the local YAML database is no longer used by ZenML 0.20.0, you will lose all the Stacks and Stack Components that you currently have configured when you update to ZenML 0.20.0. If you still want to use these Stacks, you will need to [manually migrate](migration-zero-twenty.md#-how-to-migrate-your-profiles) them after the update.
{% endhint %}

### 👣 How to migrate your Profiles

If you're already using ZenML, you can migrate your existing Profiles to the new ZenML 0.20.0 paradigm by following these steps:

1. first, update ZenML to 0.20.0. This will automatically invalidate all your existing Profiles.
2. decide the ZenML deployment model that you want to follow for your projects. See the [ZenML deployment documentation](../../user-guide/getting-started/deploying-zenml/deploying-zenml.md) for available deployment scenarios. If you decide on using a local or remote ZenML server to manage your pipelines, make sure that you first connect your client to it by running `zenml connect`.
3. use the `zenml profile list` and `zenml profile migrate` CLI commands to import the Stacks and Stack Components from your Profiles into your new ZenML deployment. If you have multiple Profiles that you would like to migrate, you can either use a prefix for the names of your imported Stacks and Stack Components, or you can use a different ZenML Project for each Profile.

{% hint style="warning" %}
The ZenML Dashboard is currently limited to showing only information that is available in the `default` Project. If you wish to migrate your Profiles to a different Project, you will not be able to visualize the migrated Stacks and Stack Components in the Dashboard. This will be fixed in a future release.
{% endhint %}

Once you've migrated all your Profiles, you can delete the old YAML files.

Example of migrating a `default` profile into the `default` project:

```bash
$ zenml profile list
ZenML profiles have been deprecated and removed in this version of ZenML. All
stacks, stack components, flavors etc. are now stored and managed globally,
either in a local database or on a remote ZenML server (see the `zenml up` and
`zenml connect` commands). As an alternative to profiles, you can use projects
as a scoping mechanism for stacks, stack components and other ZenML objects.

The information stored in legacy profiles is not automatically migrated. You can
do so manually by using the `zenml profile list` and `zenml profile migrate` commands.
Found profile with 1 stacks, 3 components and 0 flavors at: /home/stefan/.config/zenml/profiles/default
Found profile with 3 stacks, 6 components and 0 flavors at: /home/stefan/.config/zenml/profiles/zenprojects
Found profile with 3 stacks, 7 components and 0 flavors at: /home/stefan/.config/zenml/profiles/zenbytes

$ zenml profile migrate /home/stefan/.config/zenml/profiles/default
No component flavors to migrate from /home/stefan/.config/zenml/profiles/default/stacks.yaml...
Migrating stack components from /home/stefan/.config/zenml/profiles/default/stacks.yaml...
Created artifact_store 'cloud_artifact_store' with flavor 's3'.
Created container_registry 'cloud_registry' with flavor 'aws'.
Created container_registry 'local_registry' with flavor 'default'.
Created model_deployer 'eks_seldon' with flavor 'seldon'.
Created orchestrator 'cloud_orchestrator' with flavor 'kubeflow'.
Created orchestrator 'kubeflow_orchestrator' with flavor 'kubeflow'.
Created secrets_manager 'aws_secret_manager' with flavor 'aws'.
Migrating stacks from /home/stefan/.config/zenml/profiles/v/stacks.yaml...
Created stack 'cloud_kubeflow_stack'.
Created stack 'local_kubeflow_stack'.

$ zenml stack list
Using the default local database.
Running with active project: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME           │ STACK ID                             │ SHARED │ OWNER   │ CONTAINER_REGISTRY │ ARTIFACT_STORE       │ ORCHESTRATOR          │ MODEL_DEPLOYER │ SECRETS_MANAGER    ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼────────────────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┨
┃        │ local_kubeflow_stack │ 067cc6ee-b4da-410d-b7ed-06da4c983145 │        │ default │ local_registry     │ default              │ kubeflow_orchestrator │                │                    ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼────────────────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┨
┃        │ cloud_kubeflow_stack │ 054f5efb-9e80-48c0-852e-5114b1165d8b │        │ default │ cloud_registry     │ cloud_artifact_store │ cloud_orchestrator    │ eks_seldon     │ aws_secret_manager ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼────────────────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┨
┃   👉   │ default              │ fe913bb5-e631-4d4e-8c1b-936518190ebb │        │ default │                    │ default              │ default               │                │                    ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```

Example of migrating a profile into the `default` project using a name prefix:

```bash
$ zenml profile migrate /home/stefan/.config/zenml/profiles/zenbytes --prefix zenbytes_
No component flavors to migrate from /home/stefan/.config/zenml/profiles/zenbytes/stacks.yaml...
Migrating stack components from /home/stefan/.config/zenml/profiles/zenbytes/stacks.yaml...
Created artifact_store 'zenbytes_s3_store' with flavor 's3'.
Created container_registry 'zenbytes_ecr_registry' with flavor 'default'.
Created experiment_tracker 'zenbytes_mlflow_tracker' with flavor 'mlflow'.
Created experiment_tracker 'zenbytes_mlflow_tracker_local' with flavor 'mlflow'.
Created model_deployer 'zenbytes_eks_seldon' with flavor 'seldon'.
Created model_deployer 'zenbytes_mlflow' with flavor 'mlflow'.
Created orchestrator 'zenbytes_eks_orchestrator' with flavor 'kubeflow'.
Created secrets_manager 'zenbytes_aws_secret_manager' with flavor 'aws'.
Migrating stacks from /home/stefan/.config/zenml/profiles/zenbytes/stacks.yaml...
Created stack 'zenbytes_aws_kubeflow_stack'.
Created stack 'zenbytes_local_with_mlflow'.

$ zenml stack list
Using the default local database.
Running with active project: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME           │ STACK ID             │ SHARED │ OWNER   │ ORCHESTRATOR          │ ARTIFACT_STORE    │ CONTAINER_REGISTRY   │ SECRETS_MANAGER       │ MODEL_DEPLOYER      │ EXPERIMENT_TRACKER   ┃
┠────────┼──────────────────────┼──────────────────────┼────────┼─────────┼───────────────────────┼───────────────────┼──────────────────────┼───────────────────────┼─────────────────────┼──────────────────────┨
┃        │ zenbytes_aws_kubeflo │ 9fe90f0b-2a79-47d9-8 │        │ default │ zenbytes_eks_orchestr │ zenbytes_s3_store │ zenbytes_ecr_registr │ zenbytes_aws_secret_m │ zenbytes_eks_seldon │                      ┃
┃        │ w_stack              │ f80-04e45ff02cdb     │        │         │ ator                  │                   │ y                    │ anager                │                     │                      ┃
┠────────┼──────────────────────┼──────────────────────┼────────┼─────────┼───────────────────────┼───────────────────┼──────────────────────┼───────────────────────┼─────────────────────┼──────────────────────┨
┃   👉   │ default              │ 7a587e0c-30fd-402f-a │        │ default │ default               │ default           │                      │                       │                     │                      ┃
┃        │                      │ 3a8-03651fe1458f     │        │         │                       │                   │                      │                       │                     │                      ┃
┠────────┼──────────────────────┼──────────────────────┼────────┼─────────┼───────────────────────┼───────────────────┼──────────────────────┼───────────────────────┼─────────────────────┼──────────────────────┨
┃        │ zenbytes_local_with_ │ c2acd029-8eed-4b6e-a │        │ default │ default               │ default           │                      │                       │ zenbytes_mlflow     │ zenbytes_mlflow_trac ┃
┃        │ mlflow               │ d19-91c419ce91d4     │        │         │                       │                   │                      │                       │                     │ ker                  ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```

Example of migrating a profile into a new project:

```bash
$ zenml profile migrate /home/stefan/.config/zenml/profiles/zenprojects --project zenprojects
Unable to find ZenML repository in your current working directory (/home/stefan/aspyre/src/zenml) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
Creating project zenprojects
Creating default stack for user 'default' in project zenprojects...
No component flavors to migrate from /home/stefan/.config/zenml/profiles/zenprojects/stacks.yaml...
Migrating stack components from /home/stefan/.config/zenml/profiles/zenprojects/stacks.yaml...
Created artifact_store 'cloud_artifact_store' with flavor 's3'.
Created container_registry 'cloud_registry' with flavor 'aws'.
Created container_registry 'local_registry' with flavor 'default'.
Created model_deployer 'eks_seldon' with flavor 'seldon'.
Created orchestrator 'cloud_orchestrator' with flavor 'kubeflow'.
Created orchestrator 'kubeflow_orchestrator' with flavor 'kubeflow'.
Created secrets_manager 'aws_secret_manager' with flavor 'aws'.
Migrating stacks from /home/stefan/.config/zenml/profiles/zenprojects/stacks.yaml...
Created stack 'cloud_kubeflow_stack'.
Created stack 'local_kubeflow_stack'.

$ zenml project set zenprojects
Currently the concept of `project` is not supported within the Dashboard. The Project functionality will be completed in the coming weeks. For the time being it is recommended to stay within the `default` 
project.
Using the default local database.
Running with active project: 'default' (global)
Set active project 'zenprojects'.

$ zenml stack list
Using the default local database.
Running with active project: 'zenprojects' (global)
The current global active stack is not part of the active project. Resetting the active stack to default.
You are running with a non-default project 'zenprojects'. Any stacks, components, pipelines and pipeline runs produced in this project will currently not be accessible through the dashboard. However, this will be possible in the near future.
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME           │ STACK ID                             │ SHARED │ OWNER   │ ARTIFACT_STORE       │ ORCHESTRATOR          │ MODEL_DEPLOYER │ CONTAINER_REGISTRY │ SECRETS_MANAGER    ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┼────────────────────┨
┃   👉   │ default              │ 3ea77330-0c75-49c8-b046-4e971f45903a │        │ default │ default              │ default               │                │                    │                    ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┼────────────────────┨
┃        │ cloud_kubeflow_stack │ b94df4d2-5b65-4201-945a-61436c9c5384 │        │ default │ cloud_artifact_store │ cloud_orchestrator    │ eks_seldon     │ cloud_registry     │ aws_secret_manager ┃
┠────────┼──────────────────────┼──────────────────────────────────────┼────────┼─────────┼──────────────────────┼───────────────────────┼────────────────┼────────────────────┼────────────────────┨
┃        │ local_kubeflow_stack │ 8d9343ac-d405-43bd-ab9c-85637e479efe │        │ default │ default              │ kubeflow_orchestrator │                │ local_registry     │                    ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```

The `zenml profile migrate` CLI command also provides command line flags for cases in which the user wants to overwrite existing components or stacks, or ignore errors.

## Decoupling Stack Component configuration from implementation

Stack components can now be registered without having the required integrations installed. As part of this change, we split all existing stack component definitions into three classes: an implementation class that defines the logic of the stack component, a config class that defines the attributes and performs input validations, and a flavor class that links implementation and config classes together. See [**component flavor models #895**](https://github.com/zenml-io/zenml/pull/895) for more details.

If you are only using stack component flavors that are shipped with the zenml Python distribution, this change has no impact on the configuration of your existing stacks. However, if you are currently using custom stack component implementations, you will need to update them to the new format. See the [documentation on writing custom stack component flavors](../../how-to/stack-deployment/implement-a-custom-stack-component.md) for updated information on how to do this.

## Shared ZenML Stacks and Stack Components

With collaboration being the key part of ZenML, the 0.20.0 release puts the concepts of Users in the front and center and introduces the possibility to share stacks and stack components with other users by means of the ZenML server.

When your client is connected to a ZenML server, entities such as Stacks, Stack Components, Stack Component Flavors, Pipelines, Pipeline Runs, and artifacts are scoped to a Project and owned by the User that creates them. Only the objects that are owned by the current user used to authenticate to the ZenML server and that are part of the current project are available to the client.

Stacks and Stack Components can also be shared within the same project with other users. To share an object, either set it as shared during creation time (e.g. `zenml stack register mystack ... --share`) or afterwards (e.g. through `zenml stack share mystack`).

To differentiate between shared and private Stacks and Stack Components, these can now be addressed by name, id or the first few letters of the id in the cli. E.g. for a stack `default` with id `179ebd25-4c5b-480f-a47c-d4f04e0b6185` you can now run `zenml stack describe default` or `zenml stack describe 179` or `zenml stack describe 179ebd25-4c5b-480f-a47c-d4f04e0b6185`.

We also introduce the notion of `local` vs `non-local` stack components. Local stack components are stack components that are configured to run locally while non-local stack components are configured to run remotely or in a cloud environment. Consequently:

* stacks made up of local stack components should not be shared on a central ZenML Server, even though this is not enforced by the system.
* stacks made up of non-local stack components are only functional if they are shared through a remotely deployed ZenML Server.

Read more about shared stacks in the new [starter guide](../../user-guide/starter-guide/stacks/managing-stacks.md#sharing-stacks-over-a-zenml-server).

## Other changes

### The `Repository` class is now called `Client`

The `Repository` object has been renamed to `Client` to better capture its functionality. You can continue to use the `Repository` object for backwards compatibility, but it will be removed in a future release.

**How to migrate**: Rename all references to `Repository` in your code to `Client`.

### The `BaseStepConfig` class is now called `BaseParameters`

The `BaseStepConfig` object has been renamed to `BaseParameters` to better capture its functionality. You can NOT continue to use the `BaseStepConfig`.

This is part of a broader configuration rehaul which is discussed next.

**How to migrate**: Rename all references to `BaseStepConfig` in your code to `BaseParameters`.

### Configuration Rework

Alongside the architectural shift, Pipeline configuration has been completely rethought. This video gives an overview of how configuration has changed with ZenML in the post ZenML 0.20.0 world.

{% embed url="https://www.youtube.com/embed/hI-UNV7uoNI" %}
Configuring pipelines, steps, and stack components in ZenML
{% endembed %}

**What changed?**

ZenML pipelines and steps could previously be configured in many different ways:

* On the `@pipeline` and `@step` decorators (e.g. the `requirements` variable)
* In the `__init__` method of the pipeline and step class
* Using `@enable_xxx` decorators, e.g. `@enable_mlflow`.
* Using specialized methods like `pipeline.with_config(...)` or `step.with_return_materializer(...)`

Some of the configuration options were quite hidden, difficult to access and not tracked in any way by the ZenML metadata store.

With ZenML 0.20.0, we introduce the `BaseSettings` class, a broad class that serves as a central object to represent all runtime configuration of a pipeline run (apart from the `BaseParameters`).

Pipelines and steps now allow all configurations on their decorators as well as the `.configure(...)` method. This includes configurations for stack components that are not infrastructure-related which was previously done using the `@enable_xxx` decorators). The same configurations can also be defined in a YAML file.

Read more about this paradigm in the [new docs section about settings](../../how-to/use-configuration-files/what-can-be-configured.md).

Here is a list of changes that are the most obvious in consequence of the above code. Please note that this list is not exhaustive, and if we have missed something let us know via [Slack](https://zenml.io/slack).

**Deprecating the `enable_xxx` decorators**

With the above changes, we are deprecating the much-loved `enable_xxx` decorators, like `enable_mlflow` and `enable_wandb`.

**How to migrate**: Simply remove the decorator and pass something like this instead to step directly:

```python
@step(
    experiment_tracker="mlflow_stack_comp_name",  # name of registered component
    settings={  # settings of registered component
        "experiment_tracker.mlflow": {  # this is `category`.`flavor`, so another example is `step_operator.spark`
            "experiment_name": "name",
            "nested": False
        }
    }
)
```

**Deprecating `pipeline.with_config(...)`**

**How to migrate**: Replaced with the new `pipeline.run(config_path=...)`.

**Deprecating `step.with_return_materializer(...)`**

**How to migrate**: Simply remove the `with_return_materializer` method and pass something like this instead to step directly:

```python
@step(
  output_materializers=materializer_or_dict_of_materializers_mapped_to_outputs
)
```

**`DockerConfiguration` is now renamed to `DockerSettings`**

**How to migrate**: Rename `DockerConfiguration` to `DockerSettings` and instead of passing it in the decorator directly with `docker_configuration`, you can use:

```python
from zenml.config import DockerSettings

@step(settings={"docker": DockerSettings(...)})
def my_step() -> None:
  ...
```

With this change, all stack components (e.g. Orchestrators and Step Operators) that accepted a `docker_parent_image` as part of its Stack Configuration should now pass it through the `DockerSettings` object.

Read more [here](../../user-guide/starter-guide/production-fundamentals/containerization.md).

**`ResourceConfiguration` is now renamed to `ResourceSettings`**

**How to migrate**: Rename `ResourceConfiguration` to `ResourceSettings` and instead of passing it in the decorator directly with `resource_configuration`, you can use:

```python
from zenml.config import ResourceSettings

@step(settings={"resources": ResourceSettings(...)})
def my_step() -> None:
  ...
```

**Deprecating the `requirements` and `required_integrations` parameters**

Users used to be able to pass `requirements` and `required_integrations` directly in the `@pipeline` decorator, but now need to pass them through settings:

**How to migrate**: Simply remove the parameters and use the `DockerSettings` instead

```python
from zenml.config import DockerSettings

@step(settings={"docker": DockerSettings(requirements=[...], requirements_integrations=[...])})
def my_step() -> None:
  ...
```

Read more [here](../../user-guide/starter-guide/production-fundamentals/containerization.md).

**A new pipeline intermediate representation**

All the aforementioned configurations as well as additional information required to run a ZenML pipelines are now combined into an intermediate representation called `PipelineDeployment`. Instead of the user-facing `BaseStep` and `BasePipeline` classes, all the ZenML orchestrators and step operators now use this intermediate representation to run pipelines and steps.

**How to migrate**: If you have written a [custom orchestrator](../../user-guide/component-gallery/orchestrators/custom.md) or [step operator](../../user-guide/component-gallery/step-operators/custom.md), then you should see the new base abstractions (seen in the links). You can adjust your stack component implementations accordingly.

### `PipelineSpec` now uniquely defines pipelines

Once a pipeline has been executed, it is represented by a `PipelineSpec` that uniquely identifies it. Therefore, users are no longer able to edit a pipeline once it has been run once. There are now three options to get around this:

* Pipeline runs can be created without being associated with a pipeline explicitly: We call these `unlisted` runs. Read more about unlisted runs [here](../../user-guide/starter-guide/pipelines/pipelines.md#unlisted-runs).
* Pipelines can be deleted and created again.
* Pipelines can be given unique names each time they are run to uniquely identify them.

**How to migrate**: No code changes, but rather keep in mind the behavior (e.g. in a notebook setting) when quickly [iterating over pipelines as experiments](../../user-guide/starter-guide/pipelines/parameters-and-caching.md).

### New post-execution workflow

The Post-execution workflow has changed as follows:

* The `get_pipelines` and `get_pipeline` methods have been moved out of the `Repository` (i.e. the new `Client` ) class and lie directly in the post\_execution module now. To use the user has to do:

```python
from zenml.post_execution import get_pipelines, get_pipeline
```

* New methods to directly get a run have been introduced: `get_run` and `get_unlisted_runs` method has been introduced to get unlisted runs.

Usage remains largely similar. Please read the [new docs for post-execution](../../user-guide/starter-guide/pipelines/fetching-pipelines.md) to inform yourself of what further has changed.

**How to migrate**: Replace all post-execution workflows from the paradigm of `Repository.get_pipelines` or `Repository.get_pipeline_run` to the corresponding post\_execution methods.

## 📡Future Changes

While this rehaul is big and will break previous releases, we do have some more work left to do. However we also expect this to be the last big rehaul of ZenML before our 1.0.0 release, and no other release will be so hard breaking as this one. Currently planned future breaking changes are:

* Following the metadata store, the secrets manager stack component might move out of the stack.
* ZenML `StepContext` might be deprecated.

## 🐞 Reporting Bugs

While we have tried our best to document everything that has changed, we realize that mistakes can be made and smaller changes overlooked. If this is the case, or you encounter a bug at any time, the ZenML core team and community are available around the clock on the growing [Slack community](https://zenml.io/slack).

For bug reports, please also consider submitting a [GitHub Issue](https://github.com/zenml-io/zenml/issues/new/choose).

Lastly, if the new changes have left you desiring a feature, then consider adding it to our [public feature voting board](https://zenml.io/discussion). Before doing so, do check what is already on there and consider upvoting the features you desire the most.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
