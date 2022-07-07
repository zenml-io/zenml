---
description: What are stacks, profiles, and repositories in ZenML?
---

# Stacks, Profiles, Repositories

## Stacks

## Profiles

ZenML implicitly stores all the information about the configured Stacks, Stack
Components, and Stack Component Flavors in [a central location](../developer-guide/repo-and-config.md)
on the filesystem of the machine where it is installed. The details of how ZenML
stores this persistent data, where it is located, and how it is accessed can be
controlled through the ZenML **Profile** configuration.

Profiles are global ZenML management contexts that form the foundation of
ZenML's collaboration features. This guide walks you through the various ways in
which Profiles allow you to manage ZenML in multi-user and multi-host
use-cases of increasing complexity. Continue reading to learn more about ZenML
Profiles and how they can be configured to match your organizational needs:

* [The default Profile](#the-default-profile) comes pre-installed with ZenML
and only offers the most basic functionality.
* Create additional local Profiles to manage [multiple ZenML instances on a single host](#multi-instance-zenml).
* Use a different [store driver for your Profile](#shared-zenml-stores)
to store ZenML information in a remote shared location and make Stack
configurations available to multiple users and multiple hosts.

### The default Profile

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
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

Unless otherwise configured, this is the factory default ZenML setting in which
all Stacks and associated configurations are visible and shared by all ZenML
users and projects present on a machine. Configuring additional Profiles or
replacing the default Profile can unlock more possibilities for collaboration in
the context of the same host or even across multiple hosts.

### Multi-Instance ZenML

Multiple Profiles can be created on the same machine to simulate the experience
of using several independent ZenML instances completely isolated from each
other. The same or even different users can then manage their projects in the
context of different Profiles on the same host without having to worry
about overwriting each other's configuration.

To create a new local Profile, simply run `zenml profile create`:

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
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃        │ zenml        │ local      │ file:///home/stefan/.c… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

A Profile can be set as the active Profile by running `zenml profile set`.
The active Profile determines the Stacks and Stack Components that are
available for use by ZenML pipelines. New Stacks and Stack Components
registered via the CLI are only added to the active Profile and are available
only as long as that Profile is active.

The following example creates a new Profile named `zenml`, sets it as active
and then shows how the `default` Profile is unaffected by the operations
performed while the `zenml` Profile is active:

```
$ zenml profile set zenml
Running without an active repository root.
Running with active profile: 'default' (global)
Active profile changed to: 'zenml'

$ zenml profile list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃        │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃   👉   │ zenml        │ local      │ file:///home/stefan/.c… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml stack register custom -m default -a default -o default
Running without an active repository root.
Running with active profile: 'zenml' (global)
Registered stack with name 'custom'.
Stack 'custom' successfully registered!

$ zenml stack set custom
Running without an active repository root.
Running with active profile: 'zenml' (global)
Active stack set to: 'custom'

$ zenml stack list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ custom     │ default        │ default        │ default      ┃
┃        │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml profile list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃        │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃   👉   │ zenml        │ local      │ file:///home/stefan/.c… │ custom       ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml profile set default
Running without an active repository root.
Running with active profile: 'zenml' (global)
Active profile changed to: 'default'

$ zenml stack list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

From the above example, you may have also noticed that _the active Profile_ and
_the active Stack_ are global settings that affect all other user sessions open
on the same machine. It is however possible to set the active Profile and active
Stack individually for each user session or project. Keep reading to learn more.

#### Session Level Settings with Environment Variables

The global active Profile and global active Stack can be overridden by using the
environment variables `ZENML_ACTIVATED_PROFILE` and `ZENML_ACTIVATED_STACK`,
as shown in the following example:

```
$ zenml profile list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃        │ zenml        │ local      │ file:///home/stefan/.c… │ custom       ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ export ZENML_ACTIVATED_PROFILE=zenml
$ export ZENML_ACTIVATED_STACK=default

$ zenml profile list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃        │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃   👉   │ zenml        │ local      │ file:///home/stefan/.c… │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml stack list
Running without an active repository root.
Running with active profile: 'zenml' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┃        │ custom     │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

#### Project Level Settings with ZenML Repositories

When running inside an initialized [ZenML Repository](../developer-guide/repo-and-config.md),
the active Profile and active Stack can also be configured locally,
independently of the global settings, just for that particular Repository. The
following example shows how the active Profile and active Stack can be
configured locally for a project without impacting the global settings:

```
/tmp/zenml$ zenml profile list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃        │ zenml        │ local      │ file:///home/stefan/.c… │ custom       ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml init
ZenML repository initialized at /tmp/zenml.
The local active profile was initialized to 'default' and the local active stack
to 'default'. This local configuration will only take effect when you're running
ZenML from the initialized repository root, or from a subdirectory. For more
information on profile and stack configuration, please visit https://docs.zenml.io.

/tmp/zenml$ zenml profile list
Running with active profile: 'default' (local)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃        │ zenml        │ local      │ file:///home/stefan/.c… │ custom       ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml profile set zenml
Running with active profile: 'default' (local)
Active profile changed to: 'zenml'

/tmp/zenml$ zenml stack list
Running with active profile: 'zenml' (local)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃        │ default    │ default        │ default        │ default      ┃
┃   👉   │ custom     │ default        │ default        │ default      ┃
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
┃        │ custom     │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ cd ..
/tmp$ zenml profile list
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME │ STORE TYPE │ URL                     │ ACTIVE STACK ┃
┠────────┼──────────────┼────────────┼─────────────────────────┼──────────────┨
┃   👉   │ default      │ local      │ file:///home/stefan/.c… │ default      ┃
┃        │ zenml        │ local      │ file:///home/stefan/.c… │ custom       ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

Note that the Stacks and Stack Components are still stored globally, even when
running from inside a ZenML Repository. It is only the active Profile and active
Stack settings that can be configured locally.

### Migrating Stacks from Legacy Repositories to ZenML Profiles

Traditionally, Stack configurations were stored locally in the Repository root
directory - i.e. the local `.zen` folder that is created by the `zenml init`
command. The ZenML 0.7.0 release moves Stacks outside of Repository root
folders into the [global configuration directory](../developer-guide/repo-and-config.md).
The Profile concept was also introduced to replace the Repository as the
concept that manages and stores the Stack configurations.

To ensure a seamless transition from the traditional Repository root storage
to Profiles, ZenML automatically detects and migrates the Stacks from an
already initialized Repository root to a newly created Profile. This happens
automatically the first time ZenML is launched from within a legacy initialized
Repository, as demonstrated below:

```
/tmp/zenml$ zenml profile list
A legacy ZenML repository with locally configured stacks was found at 
'/tmp/zenml/.zen'.
Beginning with ZenML 0.7.0, stacks are no longer stored inside the ZenML 
repository root, they are stored globally using the newly introduced concept of
Profiles.

The stacks configured in this repository will be automatically migrated to a 
newly created profile: 'legacy-repository-b8133fe0'.

If you no longer need to use the stacks configured in this repository, please 
delete the profile using the following command:

'zenml profile delete legacy-repository-b8133fe0'

More information about Profiles can be found at https://docs.zenml.io.
This warning will not be shown again for this Repository.
Initializing profile legacy-repository-b8133fe0...
Running with active profile: 'legacy-repository-b8133fe0' (local)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ PROFILE NAME       │ STORE TYPE │ URL               │ ACTIVE STACK ┃
┠────────┼────────────────────┼────────────┼───────────────────┼──────────────┨
┃        │ default            │ local      │ file:///home/ste… │ default      ┃
┃        │ zenml              │ local      │ file:///home/ste… │ custom       ┃
┃   👉   │ legacy-repository… │ local      │ file:///tmp/zenm… │ local_stack  ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml profile describe
Running with active profile: 'legacy-repository-b8133fe0' (local)
    'legacy-repository-b8133fe0' Profile     
           Configuration (ACTIVE)            
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                      ┃
┠──────────────┼────────────────────────────┨
┃ NAME         │ legacy-repository-b8133fe0 ┃
┠──────────────┼────────────────────────────┨
┃ STORE_URL    │ file:///tmp/zenml/.zen     ┃
┠──────────────┼────────────────────────────┨
┃ STORE_TYPE   │ local                      ┃
┠──────────────┼────────────────────────────┨
┃ ACTIVE_STACK │ local_stack                ┃
┠──────────────┼────────────────────────────┨
┃ ACTIVE_USER  │ default                    ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

/tmp/zenml$ zenml stack list
Running with active profile: 'legacy-repository-b8133fe0' (local)
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME      │ ARTIFACT_STORE  │ CONTAINER_REGI… │ METADATA_STORE   │ ORCHESTRATOR    ┃
┠────────┼─────────────────┼─────────────────┼─────────────────┼──────────────────┼─────────────────┨
┃        │ local_kubeflow… │ local_artifact… │ local_registry  │ local_metadata_… │ kubeflow_orche… ┃
┃   👉   │ local_stack     │ local_artifact… │                 │ local_metadata_… │ local_orchestr… ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┛
```

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
