---
description: Centralized ZenML Stack Management with Profiles.
---

# Profiles

Profiles are configuration contexts that can be used to manage multiple
individual ZenML global configurations on the same machine. ZenML Stacks and
Stack Components, as well as the active Stack can be configured for a Profile
independently of other Profiles and referenced in ZenML Repositories.

Traditionally, Stack configurations were stored locally in the Repository root
directory - i.e. the local .zen folder that is created by the `zenml init` command.
The ZenML 0.7.0 release moves Stacks outside of Repository root folders, into the
global configuration location (e.g. under `~/.config/zenml` on Unix,
`~/Library/Application Support/zenml` on MacOS and `C:\Users\<user>\AppData\Local\zenml`
on Windows). The Profile concept was also introduced to replace the Repository
as the component that manages and stores the Stack configurations. This allows
ZenML users to configure and use the same Stacks across multiple Repositories
and even across multiple machines, in a team setting.

## The `default` Profile

A `default` Profile is created automatically and set as the active Profile the
first time ZenML runs on a machine:

```
$ zenml profile list
Creating default profile...
Initializing profile `default`...
Initializing store...
Registered stack component with type 'orchestrator' and name 'default'.
Registered stack component with type 'metadata_store' and name 'default'.
Registered stack component with type 'artifact_store' and name 'default'.
Registered stack with name 'default'.
Created and activated default profile.
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL               │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼───────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/ste… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

## Profile Configuration and Storage

Additional Profiles can be created by running `zenml profile create`. Every
Profile, including the `default` profile will have a `default` local Stack
automatically registered and set as the active Stack for that Profile.

Newly created Profiles use the default `local` store back-end that saves the
Stack configuration data on disk, in the global configuration location, as a set
of YAML files. The store driver can be changed by running `zenml profile create`
and passing a custom `--store-type` argument. Currently possible options are:

* `local` to store in yaml files on your local filesystem
* `sql` to store directly in a SQLAlchemy compatible database
* `rest` to connect to a ZenML Service over the network

Creating a new profile without setting this flag defaults to initializing a
fresh `local` store in your zenml configuration directory:

```
$ zenml profile create zenml
Running without an active repository root.
Running with active profile: 'default' (global)
Initializing profile `zenml`...
Initializing store...
Registered stack component with type 'orchestrator' and name 'default'.
Registered stack component with type 'metadata_store' and name 'default'.
Registered stack component with type 'artifact_store' and name 'default'.
Registered stack with name 'default'.
Profile 'zenml' successfully created.

$ zenml profile list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL               │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼───────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/ste… │ default      ┃
┃        │ zenml        │ local      │ file:///home/ste… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

Another possible store driver is an `sql` store, which is based on SQLAlchemy
and can interface with any SQL database service, local or remote, to store the
Stack configuration data in a SQL database.

For a local sqlite back-end, the command to create a new Profile would look
like this:

```
$ zenml profile create --store-type sql --url "sqlite:///tmp/zenml/zenml.db" sqlite_profile
Running without an active repository root.
Running with active profile: 'devel' (global)
Initializing profile `sqlite_profile`...
Profile 'sqlite_profile' successfully created.

$ zenml profile list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME   │ STORE TYPE │ URL                                                │ ACTIVE STACK ┃
┠────────┼────────────────┼────────────┼────────────────────────────────────────────────────┼──────────────┨
┃   👉   │ default        │ local      │ file:///home/stefan/.config/zenml/profiles/default │ default      ┃
┃        │ devel          │ local      │ file:///home/stefan/.config/zenml/profiles/devel   │ default      ┃
┃        │ sqlite_profile │ sql        │ sqlite:///tmp/zenml/zenml.db                       │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml profile set sqlite_profile
Running without an active repository root.
Running with active profile: 'default' (global)
Active profile changed to: 'sqlite_profile'

$ zenml stack list
Running without an active repository root.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

To connect ZenML to an existing MySQL database, some additional configuration is
required on the MySQL server:


```
mysql -u root
GRANT ALL PRIVILEGES ON *.* TO 'zenml'@'%' IDENTIFIED BY 'password';

mysql -u zenml -p
CREATE DATABASE zenml;
```

Then, on the client machine, some additional packages need to be installed
(check [the SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/dialects/mysql.html)
for the various MySQL drivers that are supported and how to use them):

```
sudo apt install libmysqlclient-dev
pip install mysqlclient
```

Finally, the command to create a new Profile would look like this:

```
$ zenml profile create --store-type sql --url "mysql://zenml:password@10.11.12.13/zenml" mysql_profile
```

## Sharing Stacks over the Network using the ZenML Service

You might want to exchange or collaborate on stacks with other developers or
even just work on multiple machines. While you can always zip up or check the
yaml based store files into version control, a more elegant option is to spin up
a ZenML service, which provides a REST API to store and access stacks and stack
components over the network. Starting a service locally is as simple as typing
`zenml service up`. This should start a background daemon accessible on your
local machine, by default on port 8000:

```
$ zenml service up
Provisioning resources for service 'zen_service'.
Zenml Service running at 'http://localhost:8000/'.
```

This service provides http access to the data of your currently active profile.
You can also specify to use a different profile with `--profile=$PROFILE_NAME`,
as well as change the port using `--port=$PORT`.

This service will run in the background, and can be checked on using

```sh
zenml service status
```

and shut down again using

```sh
zenml service down
```

For more details on how this service API looks, spin up the service and visit 
`http://$SERVICE_URL/docs` to see the OpenAPI specification.

When you want to configure your ZenML project to access the data from this
service, you must create a new profile that uses the `rest` store-type:

```sh
zenml profile create $PROFILE_NAME --type=rest --url=http://localhost:8000
zenml profile set $PROFILE_NAME
```

## Working with Profiles

Any Profile can be set as the active Profile by running `zenml profile set`.
The active Profile determines the Stacks and Stack Components that are
available for use by ZenML pipelines. New Stacks and Stack Components
registered via the CLI are added to the active Profile and will only be
available as long as that Profile is active.

```
$ zenml profile set zenml
Running without an active repository root.
Running with active profile: 'default' (global)
Active profile changed to: 'zenml'

$ zenml stack register local -m default -a default -o default
Running without an active repository root.
Running with active profile: 'zenml' (global)
Registered stack with name 'local'.
Stack 'local' successfully registered!

$ zenml stack set local
Running without an active repository root.
Running with active profile: 'zenml' (global)
Active stack set to: 'local'

$ zenml stack list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ default    │ default        │ default        │ default      ┃
┃   👉   │ local      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

All other ZenML commands and the ZenML pipeline themselves will run
in the context of the active Profile and will only have access to the
Stacks and Stack Components configured for that Profile.

When running inside an initialized ZenML Repository, the active Profile
and active Stack can also be configured locally, independently of the global
settings, just for that particular Repository. The Stacks and Stack Components
visible inside a Repository are still those configured for the active Profile.

```
/tmp/zenml$ zenml init
ZenML repository initialized at /tmp/zenml.
The local active profile was initialized to 'zenml' and the local active stack
to 'local'. This local configuration will only take effect when you're running
ZenML from the initialized repository root, or from a subdirectory. For more
information on profile and stack configuration, please run 'zenml profile
explain'.

/tmp/zenml$ zenml stack list
Running with active profile: 'zenml' (local)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ default    │ default        │ default        │ default      ┃
┃   👉   │ local      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml stack set default
Running with active profile: 'zenml' (local)
Active stack set to: 'default'

/tmp/zenml$ zenml stack list
Running with active profile: 'zenml' (local)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┃        │ local      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ cd ..
/tmp$ zenml stack list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ default    │ default        │ default        │ default      ┃
┃   👉   │ local      │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

## Migrating Stacks from legacy Repositories to ZenML Profiles

As previously mentioned, prior to ZenML version 0.7.0, Stacks could only be
configured inside an initialized Repository root, as they were stored locally
in the .zen folder. This is no longer the case, and the Stacks are now embedded
into the new Profile concept.

To ensure a seamless transition from the traditional Repository root storage
to Profiles, ZenML will automatically detect and migrate the Stacks from an
already initialized Repository root to a newly created Profile. This happens
the first time ZenML is launched from within a legacy initialized Repository:


```
$ zenml profile list
A legacy ZenML repository with locally configured stacks was found at `/home/stefan/aspyre/src/zenml/examples/airflow_local/.zen`.
The stacks configured in this repository will be automatically migrated to a newly created profile: `legacy-repository-dcc5765e`.

If you no longer need to use the stacks configured in this repository, please delete the profile using the following command:

`zenml profile delete legacy-repository-dcc5765e`

This warning will not be shown again.
Initializing profile `legacy-repository-dcc5765e`...
Running with active profile: 'legacy-repository-dcc5765e' (local)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME               │ STORE TYPE │ URL                                                       │ ACTIVE STACK         ┃
┠────────┼────────────────────────────┼────────────┼───────────────────────────────────────────────────────────┼──────────────────────┨
┃        │ default                    │ local      │ file:///home/stefan/.config/zenml/profiles/default        │ local_kubeflow_stack ┃
┃        │ devel                      │ local      │ file:///home/stefan/.config/zenml/profiles/devel          │ local_kubeflow_stack ┃
┃        │ sqlite_profile             │ sql        │ sqlite:///tmp/zenml/zenml.db                              │ local_kubeflow_stack ┃
┃   👉   │ legacy-repository-dcc5765e │ local      │ /home/stefan/aspyre/src/zenml/examples/airflow_local/.zen │ local_kubeflow_stack ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml stack list
Running with active profile: 'legacy-repository-dcc5765e' (local)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME           │ ARTIFACT_STORE       │ METADATA_STORE       │ ORCHESTRATOR          │ CONTAINER_REGISTRY ┃
┠────────┼──────────────────────┼──────────────────────┼──────────────────────┼───────────────────────┼────────────────────┨
┃        │ airflow_stack        │ local_artifact_store │ local_metadata_store │ airflow_orchestrator  │                    ┃
┃   👉   │ local_kubeflow_stack │ local_artifact_store │ local_metadata_store │ kubeflow_orchestrator │ local_registry     ┃
┃        │ local_stack          │ local_artifact_store │ local_metadata_store │ local_orchestrator    │                    ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```
