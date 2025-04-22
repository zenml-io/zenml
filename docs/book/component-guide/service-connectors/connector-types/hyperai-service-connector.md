---
description: Configuring HyperAI Connectors to connect ZenML to HyperAI instances.
---

# HyperAI Service Connector

The ZenML HyperAI Service Connector allows authenticating with a HyperAI instance for deployment of pipeline runs. This connector provides pre-authenticated Paramiko SSH clients to Stack Components that are linked to it.

```shell
$ zenml service-connector list-types --type hyperai
```
```shell
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃           NAME            │ TYPE       │ RESOURCE TYPES     │ AUTH METHODS │ LOCAL │ REMOTE ┃
┠───────────────────────────┼────────────┼────────────────────┼──────────────┼───────┼────────┨
┃ HyperAI Service Connector │ 🤖 hyperai │ 🤖 hyperai-instance │ rsa-key      │ ✅    │ ✅     ┃
┃                           │            │                    │ dsa-key      │       │        ┃
┃                           │            │                    │ ecdsa-key    │       │        ┃
┃                           │            │                    │ ed25519-key  │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites
The HyperAI Service Connector is part of the HyperAI integration. It is necessary to install the integration in order to use this Service Connector:

* `zenml integration install hyperai` installs the HyperAI integration

## Resource Types
The HyperAI Service Connector supports HyperAI instances.

## Authentication Methods
ZenML creates an SSH connection to the HyperAI instance in the background when using this Service Connector. It then provides these connections to stack components requiring them, such as the HyperAI Orchestrator. Multiple authentication methods are supported:

1. RSA key based authentication.
2. DSA (DSS) key based authentication.
3. ECDSA key based authentication.
4. ED25519 key based authentication.

{% hint style="warning" %}
SSH private keys configured in the connector will be distributed to all clients that use them to run pipelines with the HyperAI orchestrator. SSH keys are long-lived credentials that give unrestricted access to HyperAI instances.
{% endhint %}

When configuring the Service Connector, it is required to provide at least one hostname via `hostnames` and the `username` with which to login. Optionally, it is possible to provide an `ssh_passphrase` if applicable. This way, it is possible to use the HyperAI service connector in multiple ways:

1. Create one service connector per HyperAI instance with different SSH keys.
2. Configure a reused SSH key just once for multiple HyperAI instances, then select the individual instance when creating the HyperAI orchestrator component.

## Auto-configuration

{% hint style="info" %}
This Service Connector does not support auto-discovery and extraction of authentication credentials from HyperAI instances. If this feature is useful to you or your organization, please let us know by messaging us in [Slack](https://zenml.io/slack) or [creating an issue on GitHub](https://github.com/zenml-io/zenml/issues).
{% endhint %}

## Stack Components use

The HyperAI Service Connector can be used by the HyperAI Orchestrator to deploy pipeline runs to HyperAI instances.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
