---
description: Configuring Kubernetes Service Connectors to connect ZenML to Kubernetes clusters.
---

# Kubernetes Service Connector

The ZenML Kubernetes service connector facilitates authenticating and connecting to a Kubernetes cluster. The connector can be used to access to any generic Kubernetes cluster by providing pre-authenticated Kubernetes python clients to Stack Components that are linked to it and also allows configuring the local Kubernetes CLI (i.e. `kubectl`).

## Prerequisites

The Kubernetes Service Connector is part of the Kubernetes ZenML integration. You can either install the entire integration or use a pypi extra to install it independently of the integration:

* `pip install "zenml[connectors-kubernetes]"` installs only prerequisites for the Kubernetes Service Connector Type
* `zenml integration install kubernetes` installs the entire Kubernetes ZenML integration

A local Kubernetes CLI (i.e. `kubectl` ) and setting up local `kubectl` configuration contexts is not required to access Kubernetes clusters in your Stack Components through the Kubernetes Service Connector.

```shell
$ zenml service-connector list-types --type kubernetes
```
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃             NAME             │ TYPE          │ RESOURCE TYPES        │ AUTH METHODS │ LOCAL │ REMOTE ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────┼───────┼────────┨
┃ Kubernetes Service Connector │ 🌀 kubernetes │ 🌀 kubernetes-cluster │ password     │ ✅    │ ✅     ┃
┃                              │               │                       │ token        │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Resource Types

The Kubernetes Service Connector only supports authenticating to and granting access to a generic Kubernetes cluster. This type of resource is identified by the `kubernetes-cluster` Resource Type.

The resource name is a user-friendly cluster name configured during registration.

## Authentication Methods

Two authentication methods are supported:

1. username and password. This is not recommended for production purposes.
2. authentication token with or without client certificates.

For Kubernetes clusters that use neither username and password nor authentication tokens, such as local K3D clusters, the authentication token method can be used with an empty token. 

{% hint style="warning" %}
This Service Connector does not support generating short-lived credentials from the credentials configured in the Service Connector. In effect, this means that the configured credentials will be distributed directly to clients and used to authenticate to the target Kubernetes API. It is recommended therefore to use API tokens accompanied by client certificates if possible.
{% endhint %}

## Auto-configuration

The Kubernetes Service Connector allows fetching credentials from the local Kubernetes CLI (i.e. `kubectl`) during registration. The current Kubernetes kubectl configuration context is used for this purpose. The following is an example of lifting Kubernetes credentials granting access to a GKE cluster:

```sh
zenml service-connector register kube-auto --type kubernetes --auto-configure
```

{% code title="Example Command Output" %}
```text
Successfully registered service connector `kube-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES ┃
┠───────────────────────┼────────────────┨
┃ 🌀 kubernetes-cluster │ 35.185.95.223  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector describe kube-auto 
```

{% code title="Example Command Output" %}
```text
Service connector 'kube-auto' of type 'kubernetes' with id '4315e8eb-fcbd-4938-a4d7-a9218ab372a1' is owned by user 'default' and is 'private'.
     'kube-auto' kubernetes Service Connector Details      
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ kube-auto                            ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🌀 kubernetes                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ token                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ 35.175.95.223                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ a833e86d-b845-4584-9656-4b041335e299 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-16 21:45:33.224740           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-16 21:45:33.224743           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                  Configuration                  
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                 ┃
┠───────────────────────┼───────────────────────┨
┃ server                │ https://35.175.95.223 ┃
┠───────────────────────┼───────────────────────┨
┃ insecure              │ False                 ┃
┠───────────────────────┼───────────────────────┨
┃ cluster_name          │ 35.175.95.223         ┃
┠───────────────────────┼───────────────────────┨
┃ token                 │ [HIDDEN]              ┃
┠───────────────────────┼───────────────────────┨
┃ certificate_authority │ [HIDDEN]              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

{% hint style="info" %}
Credentials auto-discovered and lifted through the Kubernetes Service Connector might have a limited lifetime, especially if the target Kubernetes cluster is managed through a 3rd party authentication provider such a GCP or AWS. Using short-lived credentials with your Service Connectors could lead to loss of connectivity and other unexpected errors in your pipeline.
{% endhint %}

## Local client provisioning

This Service Connector allows configuring the local Kubernetes client (i.e. `kubectl`) with credentials:

```sh
zenml service-connector login kube-auto 
```

{% code title="Example Command Output" %}
```text
⠦ Attempting to configure local client using service connector 'kube-auto'...
Cluster "35.185.95.223" set.
⠇ Attempting to configure local client using service connector 'kube-auto'...
⠏ Attempting to configure local client using service connector 'kube-auto'...
Updated local kubeconfig with the cluster details. The current kubectl context was set to '35.185.95.223'.
The 'kube-auto' Kubernetes Service Connector was used to successfully configure the local Kubernetes cluster client/SDK.
```
{% endcode %}

## Stack Components use

The Kubernetes Service Connector can be used in Orchestrator and Model Deployer stack component flavors that rely on Kubernetes clusters to manage their workloads. This allows Kubernetes container workloads to be managed without the need to configure and maintain explicit Kubernetes `kubectl` configuration contexts and credentials in the target environment and in the Stack Component.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
