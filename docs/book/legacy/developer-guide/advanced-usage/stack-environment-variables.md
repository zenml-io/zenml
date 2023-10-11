---
description: How to set stacks with environment variables
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Setting Stacks with Environment Variables

Alternatively to using [Repositories](../stacks-repositories/repository.md),
the global active stack can be overridden by using the environment variables
`ZENML_ACTIVE_STACK_NAME`, as shown in the following example:

```
$ zenml stack list
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ORCHESTRATOR │ METADATA_STORE │ ARTIFACT_STORE ┃
┠────────┼────────────┼──────────────┼────────────────┼────────────────┨
┃   👉   │ default    │ default      │ default        │ default        ┃
┠────────┼────────────┼──────────────┼────────────────┼────────────────┨
┃        │ zenml      │ default      │ default        │ default        ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ export ZENML_ACTIVE_STACK_NAME=zenml

$ zenml stack list
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ORCHESTRATOR │ METADATA_STORE │ ARTIFACT_STORE ┃
┠────────┼────────────┼──────────────┼────────────────┼────────────────┨
┃        │ default    │ default      │ default        │ default        ┃
┠────────┼────────────┼──────────────┼────────────────┼────────────────┨
┃   👉   │ zenml      │ default      │ default        │ default        ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```