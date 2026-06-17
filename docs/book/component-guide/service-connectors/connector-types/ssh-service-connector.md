---
description: Configuring SSH connectors to connect ZenML to remote Linux hosts.
---

# SSH Service Connector

The ZenML SSH Service Connector stores SSH credentials for one or more remote Linux hosts. It can be linked to the [SSH orchestrator](../../orchestrators/ssh.md) and the [SSH step operator](../../step-operators/ssh.md), so both components can reuse the same SSH credentials instead of duplicating them in each stack component configuration.

```shell
zenml service-connector list-types --type ssh
```

## Prerequisites

The SSH Service Connector is part of the SSH integration:

```shell
zenml integration install ssh
```

The remote host must allow SSH key-based authentication for the configured user. For SSH stack components, the same host also needs Docker installed and available to that user.

## Resource Types

The SSH Service Connector supports the `ssh-host` resource type. A connector can be configured with multiple hostnames and then linked to individual SSH stack components by setting the component's `hostname` to one of those hosts.

## Authentication Methods

The connector supports SSH private-key authentication via the `private-key` auth method. The private key can be encrypted with a passphrase.

```shell
zenml service-connector register <CONNECTOR_NAME> \
    --type=ssh \
    --auth-method=private-key \
    --resource-type=ssh-host \
    --hostnames=<HOST_1>,<HOST_2> \
    --username=<SSH_USERNAME> \
    --ssh_private_key=@/path/to/private_key
```

{% hint style="warning" %}
SSH private keys configured in the connector are distributed to clients that use linked SSH stack components. Use a dedicated key with least-privilege access to the target hosts.
{% endhint %}

## Stack Component Use

Register an SSH stack component with the target hostname, then link the connector:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=ssh \
    --hostname=<HOST_1>

zenml orchestrator connect <ORCHESTRATOR_NAME> \
    --connector <CONNECTOR_NAME>
```

The same connector can be linked to an SSH step operator:

```shell
zenml step-operator register <STEP_OPERATOR_NAME> \
    --flavor=ssh \
    --hostname=<HOST_1>

zenml step-operator connect <STEP_OPERATOR_NAME> \
    --connector <CONNECTOR_NAME>
```

You can also keep using direct component configuration with `username`, `ssh_key_path`, or `ssh_private_key`; a linked SSH service connector takes precedence when present.

## Auto-Configuration

{% hint style="info" %}
The SSH Service Connector does not support auto-discovery of SSH credentials.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
