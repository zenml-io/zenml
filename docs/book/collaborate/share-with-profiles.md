---
description: Centralized ZenML Stack Management with Profiles.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# ZenML Profiles

ZenML implicitly stores all the information about the configured Stacks, Stack
Components, and Stack Component Flavors in [a central location](../developer-guide/repo-and-config.md)
on the filesystem of the machine where it is installed. The details of how ZenML
stores this persistent data, where it is located and how it is accessed can be
controlled through the ZenML Profile configuration.

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

## The default Profile

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

## Multi-Instance ZenML

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

### Session Level Settings with Environment Variables

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

### Project Level Settings with ZenML Repositories

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

## Shared ZenML Stores

The ZenML Store (or ZenStore) is a low-level concept used to represent the
particular driver used to store and retrieve the data that is managed through a
ZenML Profile. The ZenStore concept is not directly represented in the CLI
commands, but it is reflected in the Profile configuration and can be
manipulated by passing advanced parameters to the `zenml profile create` CLI
command. The particular ZenStore driver type and configuration used for a
Profile can be viewed by bringing up the detailed Profile description (note the
store type and URL):

```
$ zenml profile describe
Running without an active repository root.
Running with active profile: 'default' (global)
          'default' Profile Configuration (ACTIVE)           
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                       ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ NAME         │ default                                     ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ STORE_URL    │ file:///home/zenml/.config/profiles/default ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ STORE_TYPE   │ local                                       ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ ACTIVE_STACK │ default                                     ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ ACTIVE_USER  │ default                                     ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Different ZenStore types can be used to implement different deployment use-cases
with regards to where the ZenML managed data is stored and how and where it can
be accessed:

* [the `local` ZenStore](#local-zenml-store) stores Profile data in YAML files
on your local filesystem. This is the default ZenStore type and is suitable for
local development and testing. Local Profiles can also be shared between
multiple users even hosts by using some form of source version control or shared
filesystem.
* [the `sql` ZenStore](#sql-zenml-store) driver is based on [SQLAlchemy](https://www.sqlalchemy.org/)
and can interface with any SQL database service, local or remote, to store the
Profile data in a SQL database. The SQL driver is an easy way to extend ZenML to
accommodate multiple users working from multiple hosts.
* the `rest` ZenStore is a special type of store that connects via a REST API to
a remote ZenServer instance. This use-case is applicable to larger teams and
organizations that need to deploy ZenML as a dedicated service providing
centralized management of Stacks, Pipelines and other ZenML concepts. Please
consult the [ZenServer](./zenml-server.md) documentation dedicated to this
deployment model.

### Local ZenML Store

By default, newly created Profiles use the `local` ZenStore driver that stores
the Profile data on the local filesystem, in
[the global configuration directory](../developer-guide/repo-and-config.md),
as a collection of YAML files.

The YAML representation makes it suitable to commit Stack configurations and
all other information stored in the Profile into a version control system such
as Git, where they can be versioned and shared with other users.

To use a custom location for a Profile, point the ZenStore URL to a directory
on your local filesystem. For example:

```
$ zenml profile create git_store --url /tmp/zenml/.zenprofile
Running with active profile: 'default' (local)
Initializing profile git...
Registering default stack...
Registered stack component with type 'orchestrator' and name 'default'.
Registered stack component with type 'metadata_store' and name 'default'.
Registered stack component with type 'artifact_store' and name 'default'.
Registered stack with name 'default'.
Profile 'git_store' successfully created.

$ zenml profile set git_store
Running with active profile: 'default' (local)
Active profile changed to: 'git_store'

$ zenml profile describe
Running with active profile: 'git_store' (local)
  'git_store' Profile Configuration (ACTIVE)   
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                  ┃
┠──────────────┼────────────────────────┨
┃ NAME         │ git_store              ┃
┠──────────────┼────────────────────────┨
┃ STORE_URL    │ /tmp/zenml/.zenprofile ┃
┠──────────────┼────────────────────────┨
┃ STORE_TYPE   │ local                  ┃
┠──────────────┼────────────────────────┨
┃ ACTIVE_STACK │ default                ┃
┠──────────────┼────────────────────────┨
┃ ACTIVE_USER  │ default                ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Assuming the `/tmp/zenml` location used above is part of a local git
clone that is regularly synchronized with a remote server, replicating the
same Profile on another machine is straightforward: if the URL points to a
location where a Profile already exists, the Profile information is simply
loaded from the existing YAML files:

```
user@another_machine:/tmp$ git clone <git-repo-location> zenml
user@another_machine:/tmp$ cd zenml
user@another_machine:/tmp/zenml$

user@another_machine:/tmp$ zenml profile create git-clone --url ./.zenprofile
Running with active profile: 'git' (local)
Initializing profile git-clone...
Profile 'git-clone' successfully created.
```

As alternatives to version control, a Profile could be shared by using a
distributed filesystem (e.g. NFS) or by regularly syncing the folder with a
remote central repository using some other means. However, a better solution
of sharing Profiles across multiple machines is be to use
[the SQL ZenStore driver](#sql-zenml-store) to store the Profile data in
a SQL database, or to manage ZenML data through a centralized
[ZenServer](./zenml-server.md) instance.

### SQL ZenML Store

The SQL ZenStore type uses [SQLAlchemy](https://www.sqlalchemy.org/) to
store Profile data in a [local SQLite database file](#local-sqlite-profile),
on [a remote MySQL server](#mysql-profile) or any SQL compatible database system
for that matter. The URL value passed during the Profile creation controls the
type, location and other parameters for the SQL database connection. To explore
the full range of configuration options, consult the
[SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/dialects/index.html).

#### Local SQLite Profile

The simplest form of SQL-based Profile uses a SQLite file located in
[the global configuration directory](../developer-guide/repo-and-config.md):

```
$ zenml profile create sqlite_profile -t sql
Running without an active repository root.
Running with active profile: 'default' (global)
Initializing profile sqlite_profile...
Registering default stack...
Registered stack with name 'default'.
Profile 'sqlite_profile' successfully created.

$ zenml profile set sqlite_profile
Running without an active repository root.
Running with active profile: 'zenml' (global)
Active profile changed to: 'sqlite_profile'

$ zenml profile describe
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
                    'sqlite_profile' Profile Configuration (ACTIVE)                     
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                                                 ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ NAME         │ sqlite_profile                                                        ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ STORE_URL    │ sqlite:////home/stefan/.config/zenml/profiles/sqlite_profile/zenml.db ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ STORE_TYPE   │ sql                                                                   ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ ACTIVE_STACK │ default                                                               ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ ACTIVE_USER  │ default                                                               ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The location of the SQLite database can be customized during profile creation:

```
$ zenml profile create custom_sqlite -t sql --url=sqlite:////tmp/zenml/zenml_profile.db
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
Initializing profile custom_sqlite...
Registering default stack...
Registered stack with name 'default'.
Profile 'custom_sqlite' successfully created.

$ zenml profile set custom_sqlite
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
Active profile changed to: 'custom_sqlite'

$ zenml profile describe
Running without an active repository root.
Running with active profile: 'custom_sqlite' (global)
     'custom_sqlite' Profile Configuration (ACTIVE)     
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                 ┃
┠──────────────┼───────────────────────────────────────┨
┃ NAME         │ custom_sqlite                         ┃
┠──────────────┼───────────────────────────────────────┨
┃ STORE_URL    │ sqlite:////tmp/zenml/zenml_profile.db ┃
┠──────────────┼───────────────────────────────────────┨
┃ STORE_TYPE   │ sql                                   ┃
┠──────────────┼───────────────────────────────────────┨
┃ ACTIVE_STACK │ default                               ┃
┠──────────────┼───────────────────────────────────────┨
┃ ACTIVE_USER  │ default                               ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### MySQL Profile

To connect the ZenML Profile to an existing MySQL database, some additional
configuration is required on the MySQL server to create a user and database:

```
mysql -u root
GRANT ALL PRIVILEGES ON *.* TO 'zenml'@'%' IDENTIFIED BY 'password';

mysql -u zenml -p
CREATE DATABASE zenml;
```

Then, on the client machine, some additional packages need to be installed.
Check [the SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/dialects/mysql.html)
for the various MySQL drivers that are supported and how to install and use
them. The following is an example of using the [mysqlclient](https://docs.sqlalchemy.org/en/14/dialects/mysql.html#module-sqlalchemy.dialects.mysql.mysqldb)
driver for SQLAlchemy on an Ubuntu OS. Depending on your choice of driver and
host OS, your experience may vary:

```
sudo apt install libmysqlclient-dev
pip install mysqlclient
```

Finally, the command to create a new Profile would look like this:

```
$ zenml profile create --store-type sql --url "mysql://zenml:password@10.11.12.13/zenml" mysql_profile
```

## Migrating Stacks from Legacy Repositories to ZenML Profiles

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
