---
description: Configuring the OAuth2 Service Connector to connect ZenML to OAuth2-protected HTTP APIs.
---

# OAuth2 Service Connector

The ZenML OAuth2 Service Connector authenticates to an HTTP API using OAuth2 and provides connector consumers with a pre-authenticated `requests` session that has a bearer token set on the `Authorization` header. The client credentials and refresh token methods exchange long-lived credentials for a short-lived access token, so that consumers only ever receive a temporary token and never the underlying client secret or refresh token.

```shell
zenml service-connector list-types --type oauth2
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃           NAME           │ TYPE      │ RESOURCE TYPES │ AUTH METHODS                             │ LOCAL │ REMOTE ┃
┠──────────────────────────┼───────────┼────────────────┼──────────────────────────────────────────┼───────┼────────┨
┃ OAuth2 Service Connector │ 🔐 oauth2 │ 🌐 oauth2-api  │ client-credentials, refresh-token, token │ ✅    │ ✅     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites

No Python packages are required for this Service Connector. All prerequisites are included in the base ZenML Python package.

## Resource Types

The OAuth2 Service Connector supports a single resource type, `oauth2-api`, which represents an HTTP API protected by OAuth2. The resource name is the base URL of the API, for example `https://api.example.com`.

This resource type does not support multiple instances. A single connector grants access to a single API, identified by the configured `api_url`.

## Authentication Methods

The connector supports three authentication methods. Two of them exchange long-lived credentials for a temporary access token at the OAuth2 token endpoint and hand consumers only the temporary token. The third lets you supply an access token directly.

### Client credentials

Use the OAuth2 client credentials grant to authenticate as a service identity, for machine-to-machine access with no user context. Configure the token endpoint, the client ID and secret, and optionally a scope and audience.

```sh
zenml service-connector register my-api --type oauth2 --auth-method client-credentials \
    --api_url=https://api.example.com \
    --token_url=https://auth.example.com/oauth/token \
    --client_id=<CLIENT_ID> \
    --client_secret=<CLIENT_SECRET> \
    --scope="read write"
```

The client secret stays on the connector. Every consumer receives a freshly minted access token instead.

### Refresh token

Use the OAuth2 refresh token grant to authenticate as a user-delegated identity. The connector will exchange the refresh token for access tokens as needed. The client secret is optional, so public clients are supported.

```sh
zenml service-connector register my-api --type oauth2 --auth-method refresh-token \
    --api_url=https://api.example.com \
    --token_url=https://auth.example.com/oauth/token \
    --client_id=<CLIENT_ID> \
    --refresh_token=<REFRESH_TOKEN>
```

{% hint style="warning" %}
Some providers issue a new refresh token on every exchange and invalidate the previous one. These rotating refresh tokens are currently not supported. 
{% endhint %}

### Token

Supply a pre-obtained OAuth2 access token directly. The connector uses it as-is and does not refresh it.

```sh
zenml service-connector register my-api --type oauth2 --auth-method token \
    --api_url=https://api.example.com \
    --access_token=<ACCESS_TOKEN>
```

If you know when the token expires, set the connector expiration when registering so that ZenML stops using it once it is no longer valid.

## Token expiration

For the client credentials and refresh token methods, the lifetime of a minted access token is dictated by the OAuth2 server and read from the `expires_in` field of the token response. ZenML always respects the server value and does not let you request a different lifetime. If the server does not return an expiration, ZenML treats the token as non-expiring and keeps using it until the API rejects it.

## Auto-configuration

{% hint style="info" %}
This Service Connector does not support auto-discovery and extraction of authentication credentials from the local environment.
{% endhint %}

## Local client provisioning

This Service Connector does not configure a local client. OAuth2 is consumed directly through the authenticated `requests` session returned by the connector.

## How to use

No built-in Stack Component requires the `oauth2-api` resource type. This connector is intended for your use as an easy way to get credentials for accessing an OAuth2 authenticated API. A consumer obtains an authenticated `requests` session from the connector and uses it to call the API:

```python
from zenml.client import Client

client = Client()

# Get a Service Connector client for the API
connector_client = client.get_service_connector_client(
    name_id_or_prefix="my-api",
    resource_type="oauth2-api",
)

# Get a pre-authenticated requests Session from the Service Connector client
session = connector_client.connect()

# Call the API using the temporary token that was issued to the client
response = session.get("https://api.example.com/v1/resource")
```