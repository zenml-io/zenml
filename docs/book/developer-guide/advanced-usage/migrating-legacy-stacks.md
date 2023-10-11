---
description: How to migrate legacy stacks from zenml<0.7
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Migrating Legacy Stacks to ZenML Profiles

Traditionally, stack configurations were stored locally in the repository root
directory - i.e. the local `.zen` folder that is created by the `zenml init`
command. The ZenML 
[0.7.0 release](https://github.com/zenml-io/zenml/blob/main/RELEASE_NOTES.md#070)
moved stacks outside of repository root folders into the 
[Global Configuration](../../resources/global-config.md).
The profile concept was also introduced to replace the repository as the
concept that manages and stores the stack configurations.

To ensure a seamless transition from the traditional repository root storage
to profiles, ZenML automatically detects and migrates any stacks from
already initialized repository roots to a newly created profile as soon as the
ZenML is launched for the first time from within a legacy repository.

An example is shown:

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