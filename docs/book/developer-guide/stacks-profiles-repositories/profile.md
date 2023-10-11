---
description: How to manage stack configurations with profiles
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


ZenML implicitly stores all the information about the configured Stacks, Stack
Components, and Stack Component Flavors in the 
[Global Configuration](../../resources/global-config.md) on the filesystem of the
machine where it is installed. The details of how ZenML stores this persistent
data, where it is located, and how it is accessed can be configured via the 
ZenML **Profile**.

## The default Profile

The first time you run any `zenml` CLI command on a machine, a `default` 
Profile is automatically created and set as active. Unless otherwise
configured, this `default` profile will contain all stacks and stack components
that you create on your machine.

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

## Creating and Changing Profiles

Multiple Profiles can be created on the same machine to simulate the experience
of using several independent ZenML instances completely isolated from each
other. The same or even different users can then manage their projects in the
context of different Profiles on the same machine without having to worry
about overwriting existing configurations.

To create a new profile, run
```
zenml profile create <NEW_PROFILE_NAME>
```

To set an existing profile as active, run
```
zenml profile set <PROFILE_NAME>
```

{% hint style="info" %}
The active Profile determines the stacks and stack components that are
available for use by ZenML pipelines. New stacks and stack components
registered via the CLI are only added to the active profile and are available
only as long as that profile is active.

If you want to reuse stacks from other profiles, you can use the 
`zenml stack copy` CLI command to copy stacks between profiles. For more
information, run `zenml stack copy --help` or visit our
[CLI docs](https://apidocs.zenml.io/latest/cli/).
{% endhint %}

### Detailed Example

<details>
<summary>Detailed usage example of multiple profiles</summary>

The following example creates a new profile named `zenml`, sets it as active,
and then shows how the `default` profile is unaffected by the operations
performed while the `zenml` profile is active:

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

From the above example, you may have also noticed that the _Active Profile_ and
the _Active Stack_ are global settings that affect all other user sessions open
on the same machine. It is however possible to set the active profile and active
stack individually for each user session or project. Keep reading to learn more.

</details>
