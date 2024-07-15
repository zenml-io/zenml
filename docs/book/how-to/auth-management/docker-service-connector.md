---
description: Configuring Docker Service Connectors to connect ZenML to Docker container registries.
---

# Docker Service Connector

The ZenML Docker Service Connector allows authenticating with a Docker or OCI container registry and managing Docker clients for the registry. This connector provides pre-authenticated python-docker Python clients to Stack Components that are linked to it.

```shell
zenml service-connector list-types --type docker
```
```shell
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃           NAME           │ TYPE      │ RESOURCE TYPES     │ AUTH METHODS │ LOCAL │ REMOTE ┃
┠──────────────────────────┼───────────┼────────────────────┼──────────────┼───────┼────────┨
┃ Docker Service Connector │ 🐳 docker │ 🐳 docker-registry │ password     │ ✅    │ ✅     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites

No Python packages are required for this Service Connector. All prerequisites are included in the base ZenML Python package. Docker needs to be installed on environments where container images are built and pushed to the target container registry.

## Resource Types

The Docker Service Connector only supports authenticating to and granting access to a Docker/OCI container registry. This type of resource is identified by the `docker-registry` Resource Type.

The resource name identifies a Docker/OCI registry using one of the following formats (the repository name is optional and ignored).

* DockerHub: docker.io or `https://index.docker.io/v1/<repository-name>`
* generic OCI registry URI: `https://host:port/<repository-name>`

## Authentication Methods

Authenticating to Docker/OCI container registries is done with a username and password or access token. It is recommended to use API tokens instead of passwords, wherever this is available, for example in the case of DockerHub:

```sh
zenml service-connector register dockerhub --type docker -in
```

{% code title="Example Command Output" %}
```text
Please enter a name for the service connector [dockerhub]: 
Please enter a description for the service connector []: 
Please select a service connector type (docker) [docker]: 
Only one resource type is available for this connector (docker-registry).
Only one authentication method is available for this connector (password). Would you like to use it? [Y/n]: 
Please enter the configuration for the Docker username and password/token authentication method.
[username] Username {string, secret, required}: 
[password] Password {string, secret, required}: 
[registry] Registry server URL. Omit to use DockerHub. {string, optional}: 
Successfully registered service connector `dockerhub` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES ┃
┠────────────────────┼────────────────┨
┃ 🐳 docker-registry │ docker.io      ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

{% hint style="warning" %}
This Service Connector does not support generating short-lived credentials from the username and password or token credentials configured in the Service Connector. In effect, this means that the configured credentials will be distributed directly to clients and used to authenticate directly to the target Docker/OCI registry service.
{% endhint %}

## Auto-configuration

{% hint style="info" %}
This Service Connector does not support auto-discovery and extraction of authentication credentials from local Docker clients. If this feature is useful to you or your organization, please let us know by messaging us in [Slack](https://zenml.io/slack) or [creating an issue on GitHub](https://github.com/zenml-io/zenml/issues).
{% endhint %}

## Local client provisioning

This Service Connector allows configuring the local Docker client with credentials:

```sh
zenml service-connector login dockerhub
```

{% code title="Example Command Output" %}
```text
Attempting to configure local client using service connector 'dockerhub'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'dockerhub' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}

## Stack Components use

The Docker Service Connector can be used by all Container Registry stack component flavors to authenticate to a remote Docker/OCI container registry. This allows container images to be built and published to private container registries without the need to configure explicit Docker credentials in the target environment or the Stack Component.

{% hint style="warning" %}
ZenML does not yet support automatically configuring Docker credentials in container runtimes such as Kubernetes clusters (i.e. via imagePullSecrets) to allow container images to be pulled from the private container registries. This will be added in a future release.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
