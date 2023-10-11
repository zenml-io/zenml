---
description: How to set stacks and profiles with environment variables
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Setting Stacks and Profiles with Environment Variables

Alternatively to using [Repositories](../stacks-profiles-repositories/repository.md),
the global active profile and global active stack can be overridden by using the
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