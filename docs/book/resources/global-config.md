---
description: What is the global ZenML config
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# The Global Config

ZenML has two main locations where it stores information on the local machine.
These are the _Global Config_ and the _Repository_ (see 
[here](../developer-guide/stacks-profiles-repositories/repository.md)
for more information on the repository).

Most of the information stored by ZenML on a machine, such as the global
settings, the configured 
[Profiles](../developer-guide/stacks-profiles-repositories/profile.md),
and even the configured 
[Stacks and Stack Components](../developer-guide/stacks-profiles-repositories/stack.md), 
is kept in a folder commonly referred to as the _ZenML Global Config Directory_
or the _ZenML Config Path_. The location of this folder depends on the 
operating system type and the current system user, but is usually located in 
the following locations:

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
[ZenML Profiles](../developer-guide/stacks-profiles-repositories/profile.md) for more information about
Profiles.)

In addition to the above, you may also find the following files and folders under
the _Global Config Directory_, depending on what you do with ZenML:

* `zenml_examples` - used as a local cache by the `zenml example` command, where
the pulled ZenML examples are stored.
* `kubeflow` - this is where the Kubeflow orchestrators that are part of a Stack
store some of their configuration and logs.

## Accessing the global configuration in Python

You can access the global ZenML configuration from within Python using the
`zenml.config.global_config.GlobalConfiguration` class:

```python
from zenml.config.global_config import GlobalConfiguration
config = GlobalConfiguration()
```

This can be used to manage your profiles and other global settings from within
Python. For instance, we can use it to create and activate a new profile:

```python
from zenml.repository import Repository
from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration

repo = Repository()
config = GlobalConfiguration()

# Create a new profile called "local"
profile = ProfileConfiguration(name="local")
config.add_or_update_profile(profile)

# Set the profile as active profile of the repository
repo.activate_profile("local")
```

To explore all possible operations that can be performed via the 
`GlobalConfiguration`, please consult the API docs sections on 
[GlobalConfiguration](https://apidocs.zenml.io/latest/api_docs/config/#zenml.config.global_config.GlobalConfiguration).
