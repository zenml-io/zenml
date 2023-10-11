---
description: What is the global ZenML config
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# The Global Config

The information about the global settings of ZenML on a machine is kept in a 
folder commonly referred to as the _ZenML Global Config Directory_ or the 
_ZenML Config Path_. The location of this folder depends on the operating 
system type and the current system user, but is usually located in 
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
* `zenml config` - manage the global configuration
* `zenml clean` - to be used only in case of emergency, to bring the ZenML
configuration back to its default factory state

{% endhint %}

The first time that ZenML is run on a machine, it creates the _Global Config
Directory_ and initializes the default configuration in it, along with a default
Stack:

```
Initializing the ZenML global configuration version to 0.13.2
Creating default project 'default' ...
Creating default user 'default' ...
Creating default stack for user default in project default...
Active project not set. Setting it to the default.
The active stack is not set. Setting the active stack to the default project stack.
Using the default store for the global config.
Unable to find ZenML repository in your current working directory (/tmp/folder) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
Using the default local database.
Running with active project: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ SHARED │ OWNER   │ ARTIFACT_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────┼─────────┼────────────────┼──────────────┨
┃   👉   │ default    │ ❌     │ default │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

The following is an example of the layout of the _Global Config Directory_
immediately after initialization:

```
/home/stefan/.config/zenml   <- Global Config Directory
├── config.yaml              <- Global Configuration Settings
└── local_stores             <- Every Stack component that stores information
    |                           locally will have its own subdirectory here.              
    ├── a1a0d3d0-d552-4a80-be09-67e5e29be8ee   <- e.g. Local Store path for the 
    |                                             `default` local Artifact Store                                           
    └── zenml.db             <- SQLite database where ZenML data (stacks, 
                               components, etc) are stored by default.
```

As shown above, the _Global Config Directory_ stores the following
information:

1. The `global.yaml` file stores the global configuration settings: the unique
ZenML user ID, the active database configuration, the analytics related options
the active Stack and active Project. This is an example of the `global.yaml`
file contents immediately after initialization:

   ```yaml
   active_project_name: default
   active_stack_id: ...
   analytics_opt_in: true
   store:
     database: ...
     url: ...
     username: ...
     ...
   user_id: d980f13e-05d1-4765-92d2-1dc7eb7addb7
   user_metadata: null
   version: 0.13.2
   ```

2. The `local_stores` directory is where some "local" flavors of Stack Components,
such as the `local` Artifact Store, or the `local`
Secrets Manager persist data locally. Every local Stack Component will have its
own subdirectory here named after the Stack Component's unique UUID. One notable
example is the `local` Artifact Store flavor that, when part of the active Stack,
stores all the artifacts generated by Pipeline runs in the designated local
directory.

3. The `zenml.db` file is the default SQLite database where ZenML stores all
information about the Stacks, Stack Components, custom Stack Component flavors
etc.

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

This can be used to manage your global settings from within Python.

To explore all possible operations that can be performed via the 
`GlobalConfiguration`, please consult the API docs sections on 
[GlobalConfiguration](https://apidocs.zenml.io/latest/api_docs/config/#zenml.config.global_config.GlobalConfiguration).
