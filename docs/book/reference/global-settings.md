---
description: Understanding the global settings of your ZenML installation.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 📼 Global settings

The information about the global settings of ZenML on a machine is kept in a folder commonly referred to as the **ZenML Global Config Directory** or the **ZenML Config Path**. The location of this folder depends on the operating system type and the current system user, but is usually located in the following locations:

* Linux: `~/.config/zenml`
* Mac: `~/Library/Application Support/zenml`
* Windows: `C:\Users\%USERNAME%\AppData\Local\zenml`

The default location may be overridden by setting the `ZENML_CONFIG_PATH` environment variable to a custom value. The current location of the global config directory used on a system can be retrieved by running the following commands:

```shell
# The output will tell you something like this:
# Using configuration from: '/home/stefan/.config/zenml'
zenml status

python -c 'from zenml.utils.io_utils import get_global_config_directory; print(get_global_config_directory())'
```

{% hint style="warning" %}
Manually altering or deleting the files and folders stored under the ZenML global config directory is not recommended, as this can break the internal consistency of the ZenML configuration. As an alternative, ZenML provides CLI commands that can be used to manage the information stored there:

* `zenml analytics` - manage the analytics settings
* `zenml clean` - to be used only in case of emergency, to bring the ZenML configuration back to its default factory state
* `zenml downgrade` - downgrade the ZenML version in the global configuration to match the version of the ZenML package installed in the current environment. Read more about this in the [ZenML Version Mismatch](global-settings.md#version-mismatch-downgrading) section.
{% endhint %}

The first time that ZenML is run on a machine, it creates the global config directory and initializes the default configuration in it, along with a default Stack:

```
Initializing the ZenML global configuration version to 0.13.2
Creating default user 'default' ...
Creating default stack for user 'default'...
The active stack is not set. Setting the active stack to the default stack.
Using the default store for the global config.
Unable to find ZenML repository in your current working directory (/tmp/folder) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ SHARED │ OWNER   │ ARTIFACT_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────┼─────────┼────────────────┼──────────────┨
┃   👉   │ default    │ ❌     │ default │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

The following is an example of the layout of the global config directory immediately after initialization:

```
/home/stefan/.config/zenml   <- Global Config Directory
├── config.yaml              <- Global Configuration Settings
└── local_stores             <- Every Stack component that stores information 
    |                           locally will have its own subdirectory here.              
    ├── a1a0d3d0-d552-4a80-be09-67e5e29be8ee   <- e.g. Local Store path for the 
    |                                             `default` local Artifact Store                                           
    └── default_zen_store
        |
        └── zenml.db         <- SQLite database where ZenML data (stacks, 
                                components, etc) are stored by default.
```

As shown above, the global config directory stores the following information:

1.  The `config.yaml` file stores the global configuration settings: the unique
    ZenML client ID, the active database configuration, the analytics-related
    options, and the active Stack. This is an example of the `config.yaml` file
    contents immediately after initialization:

    ```yaml
    active_stack_id: ...
    analytics_opt_in: true
    store:
      database: ...
      url: ...
      username: ...
      ...
    user_id: d980f13e-05d1-4765-92d2-1dc7eb7addb7
    version: 0.13.2
    ```
2. The `local_stores` directory is where some "local" flavors of stack components, such as the local artifact store, or a local MLFlow experiment tracker, persist data locally. Every local stack component will have its own subdirectory here named after the stack component's unique UUID. One notable example is the local artifact store flavor that, when part of the active stack, stores all the artifacts generated by pipeline runs in the designated local directory.
3. The `zenml.db` in the `default_zen_store` directory is the default SQLite database where ZenML stores all information about the stacks, stack components, custom stack component flavors, etc.

In addition to the above, you may also find the following files and folders under the global config directory, depending on what you do with ZenML:

* `kubeflow` - this is where the Kubeflow orchestrators that are part of a stack store some of their configuration and logs.

## Usage analytics

In order to help us better understand how the community uses ZenML, the pip package reports **anonymized** usage statistics. You can always opt out by using the CLI command:

```bash
zenml analytics opt-out
```

#### Why does ZenML collect analytics? <a href="#motivation" id="motivation"></a>

In addition to the community at large, **ZenML** is created and maintained by a startup based in Munich, Germany called [ZenML GmbH](https://zenml.io). We're a team of techies that love MLOps and want to build tools that fellow developers would love to use in their daily work. [This is us](https://zenml.io/company#CompanyTeam) if you want to put faces to the names!

However, in order to improve **ZenML** and understand how it is being used, we need to use analytics to have an overview of how it is used 'in the wild'. This not only helps us find bugs but also helps us prioritize features and commands that might be useful in future releases. If we did not have this information, all we really get is pip download statistics and chatting with people directly, which while being valuable, is not enough to seriously better the tool as a whole.

#### How does ZenML collect these statistics? <a href="#implementation" id="implementation"></a>

We use [Segment](https://segment.com) as the data aggregation library for all our analytics. However, before any events get sent to [Segment](https://segment.com), they first go through a central ZenML analytics server. This added layer allows us to put various countermeasures to incidents such as getting spammed with events and enables us to have a more optimized tracking process.

The client code is entirely visible and can be seen in the [`analytics`](https://github.com/zenml-io/zenml/tree/main/src/zenml/analytics) module of our main repository.

#### If I share my email, will you spam me?

No, we won't. Our sole purpose of contacting you will be to ask for feedback (e.g. in the shape of a user interview). These interviews help the core team understand usage better and prioritize feature requests. If you have any concerns about data privacy and the usage of personal information, please [contact us](mailto:support@zenml.io), and we will try to alleviate any concerns as soon as possible.

## Version mismatch (downgrading)

If you've recently downgraded your ZenML version to an earlier release or installed a newer version on a different environment on the same machine, you might encounter an error message when running ZenML that says:

```shell
`The ZenML global configuration version (%s) is higher than the version of ZenML 
currently being used (%s).`
```

We generally recommend using the latest ZenML version. However, there might be cases where you need to match the global configuration version with the version of ZenML installed in the current environment. To do this, run the following command:

```shell
zenml downgrade
```

{% hint style="warning" %}
Note that downgrading the ZenML version may cause unexpected behavior, such as model schema validation failures or even data loss. In such cases, you may need to purge the local database and re-initialize the global configuration to bring it back to its default factory state. To do this, run the following command:

```shell
zenml clean
```
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
