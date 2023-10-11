---
description: What is the .zen folder and the global config?
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# The Global Config and the Repository

ZenML has two main locations where it stores information on the machine where it
is used. These are the _Global Config_ and the _Repository_. The latter is also
referred to as the _.zen folder_.

## The Global Config

Most of the information stored by ZenML on a machine, such as the global
settings, the configured [ZenML Profiles](../collaborate/share-with-profiles.md) and even
the configured Stacks and Stack Components, is kept in a folder commonly
referred to as the _ZenML Global Config Directory_ or the _ZenML Config Path_.
The location of this folder depends on the operating system type and the current
system user, but is usually located in the following locations:

* Linux: `~/.config/zenml`
* Mac: `~/Library/Application Support/ZenML`
* Windows: `C:\Users\%USERNAME%\AppData\Local\ZenML`

The default location may be overridden by setting the `ZENML_CONFIG_PATH`
environment variable to a custom value. The current location of the _Global
Config Directory_ used on a system can be retrieved by running the following
command:

```shell
python -c 'from zenml.utils.io_utils import get_global_config_directory; print(get_global_config_directory())'
```

{% hint style="warning" %}
Manually altering or deleting the files and folders stored under the _ZenML Global
Config Directory_ is not recommended, as this can break the internal consistency
of the ZenML configuration. As an alternative, ZenML provides CLI commands that
can be used to manage the information stored there:

* `zenml analytics` - manage the analytics settings
* `zenml profile` - manage configuration Profiles
* `zenml stack` - manage Stacks
* `zenml <stack-component>` - manage Stack Components
* `zenml clean` - to be used only in case of emergency, to bring the ZenML
configuration back to its default factory state

{% endhint %}

The first time that ZenML is run on a machine, it creates the _Global Config
Directory_ and initializes the default configuration in it, along with a default
Profile and Stack:

```
$ zenml stack list
Unable to find ZenML repository in your current working directory (/home/stefan)
or any parent directories. If you want to use an existing repository which is in
a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If
you want to create a new repository, run zenml init.
Initializing the ZenML global configuration version to 0.7.3
Creating default profile...
Initializing profile default...
Registering default stack...
Registered stack component with type 'orchestrator' and name 'default'.
Registered stack component with type 'metadata_store' and name 'default'.
Registered stack component with type 'artifact_store' and name 'default'.
Registered stack with name 'default'.
Created and activated default profile.
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

The following is an example of the layout of the _Global Config Directory_
immediately after initialization:

```
/home/stefan/.config/zenml   <- Global Config Directory
├── config.yaml              <- Global Configuration Settings
├── local_stores             <- Every Stack component that stores information
|   |                        locally will have its own subdirectory here.
|   |                        
│   └── 09fcdb1c-4079-4d20-afdb-957965405863   <- Local Store path for the `default`
|                                              local Artifact Store
|
└── profiles                 <- root path where Profiles data (stacks, components,
    |                        etc) are stored by default. Every Profile will have
    |                        its own subdirectory here, unless the Profile is
    |                        configured with a custom configuration path.
    |
    └── default              <- configuration folder for the `default` Profile.
        ├── artifact_stores
        │   └── default.yaml
        ├── metadata_stores
        │   └── default.yaml
        ├── orchestrators
        │   └── default.yaml
        └── stacks.yaml
```

As shown above, the _Global Config Directory_ stores the following
information:

1. The `global.yaml` file stores the global configuration settings: the unique
ZenML user ID, the active Profile, the analytics related options and a list of all configured Profiles, along with their configuration attributes, such as the
active Stack set for each Profile. This is an example of the `global.yaml` file
contents immediately after initialization:

    ```yaml
    activated_profile: default
    analytics_opt_in: true
    profiles:
    default:
        active_stack: default
        active_user: default
        name: default
        store_type: local
        store_url: file:///home/stefan/.config/zenml/profiles/default
    user_id: 4b773740-fddc-46ee-938e-1c78a075cfc7
    user_metadata: null
    version: 0.7.3
    ```

2. The `local_stores` directory is where some "local" flavors of Stack Components,
such as the `local` Artifact Store, the `sqlite` Metadata Store or the `local`
Secrets Manager persist data locally. Every local Stack Component will have its
own subdirectory here named after the Stack Component's unique UUID. One notable
example is the `local` Artifact Store flavor that, when part of the active Stack,
stores all the artifacts generated by Pipeline runs in the designated local
directory.

3. The `profiles` directory is used as a default root path location where ZenML
stores information about the Stacks, Stack Components, custom Stack Component
flavors etc. that are configured under each Profile. Every Profile will have its
own subdirectory here, unless the Profile is explicitly created with a custom
configuration path. (See the `zenml profile` command and the section on
[ZenML Profiles](../collaborate/share-with-profiles.md) for more information about
Profiles.)

In addition to the above, you may also find the following files and folders under
the _Global Config Directory_, depending on what you do with ZenML:

* `zenml_examples` - used as a local cache by the `zenml example` command, where
the pulled ZenML examples are stored.
* `kubeflow` - this is where the Kubeflow orchestrators that are part of a Stack
store some of their configuration and logs.

## The ZenML Repository

A ZenML _Repository_ designates a folder that contains a complete set of Python
scripts and modules as well as any associated files that are needed to run ZenML
pipelines. Any such folder can be registered as a ZenML Repository root by running
the `zenml init` command from that folder or passing its location as an argument
to that same command, e.g.:

```shell
stefan@aspyre2:/tmp/zenml$ zenml init
ZenML repository initialized at /tmp/zenml.
The local active profile was initialized to 'default' and the local active stack to 'default'. This local configuration will only take effect when you're running ZenML from the initialized repository root, or from a subdirectory. For more information on profile and stack configuration, please visit https://docs.zenml.io.
```

The _Repository_ designation plays a double role in ZenML:

* it is used by ZenML to identify which files it must copy into the environments
it builds that are used to execute pipeline steps remotely, such as container
images.
* it stores local configuration parameters that can be set independently of the
global configuration: the _Repository_ active Profile and active Stack. These
settings are in effect when ZenML code is executed while the current working
directory is the _Repository_ root or one of its sub-folders. For more information
on setting the active Profile and Stack local to a _Repository_, please visit
the [ZenML Profiles](../collaborate/share-with-profiles.md) section.

A ZenML _Repository_ is easily identifiable by the presence of a (hidden) `.zen`
directory located in the root folder. The `.zen` directory contains a single
`config.yaml` file that stores the local settings:

```yaml
active_profile_name: default
active_stack_name: default
```

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

To remove the _Repository_ designation from a folder, simply delete the
`.zen` subdirectory in that folder.

## The GlobalConfiguration and Repository Singletons

ZenML provides two singleton objects that can be used to access and manage the
information stored in the _Global Config Directory_ and the current _Repository_.

To access the global configuration settings and manage Profiles, you can use the
`zenml.config.global_config.GlobalConfiguration` singleton, while the
`zenml.repository.Repository` singleton acts as the central point of
management for Stacks, Stack Components, Stack Component flavors and other
associated ZenML concepts. The following are examples of how to use these
singletons to perform various operations:

* to retrieve the global configuration, active Profile and active Stack:

    ```python
    from zenml.config.global_config import GlobalConfiguration
    from zenml.repository import Repository

    repo = Repository()
    config = GlobalConfiguration()

    # the unique user UUID set
    user_id = config.user_id

    # the active profile name
    profile = repo.active_profile_name

    # the active profile object
    profile = repo.active_profile

    # the name of the active stack
    active_stack_name = config.active_stack_name

    # the active stack object
    active_stack = repo.active_stack
    ```

* to create a new Profile and set it as the active one:

    ```python
    from zenml.repository import Repository
    from zenml.config.global_config import GlobalConfiguration
    from zenml.config.profile_config import ProfileConfiguration

    repo = Repository()
    config = GlobalConfiguration()

    profile = ProfileConfiguration(name="local")
    config.add_or_update_profile(profile)

    repo.activate_profile("local")
    ```

* access the active Stack

    ```python
    from zenml.repository import Repository

    repo = Repository()
    stack = repo.active_stack
    
    print(stack.name)
    print(stack.orchestrator.name)
    print(stack.artifact_store.name)
    print(stack.artifact_store.path)
    print(stack.metadata_store.name)
    print(stack.metadata_store.uri)
    ```

* register and set a new Stack

    ```python
    from zenml.repository import Repository
    from zenml.artifact_stores import LocalArtifactStore
    from zenml.metadata_stores import SQLiteMetadataStore
    from zenml.orchestrators import LocalOrchestrator
    from zenml.stack import Stack

    repo = Repository()

    orchestrator = LocalOrchestrator(name="local")
    metadata_store = SQLiteMetadataStore(
        name="local",
        uri="/tmp/zenml/zenml.db",
    )
    artifact_store = LocalArtifactStore(
        name="local",
        path="/tmp/zenml/artifacts",
    )
    stack = Stack(
        name="local",
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
    )

    repo.register_stack(stack)
    repo.activate_stack(stack.name)
    ```

To explore all possible operations that can be performed via the `GlobalConfiguration`
and `Repository` singletons, please consult the API docs sections on [GlobalConfiguration](https://apidocs.zenml.io/latest/api_docs/config/#zenml.config.global_config.GlobalConfiguration) and [Repository](https://apidocs.zenml.io/latest/api_docs/repository/#zenml.repository.Repository).
