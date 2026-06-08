---
description: >-
  Configuring Cloudflare service connectors to connect ZenML to Cloudflare R2
  and the Cloudflare account API.
---

# Cloudflare Service Connector

The ZenML Cloudflare Service Connector brokers authenticated access to Cloudflare
resources for ZenML stack components. It is the single point of authentication
that hands components pre-authenticated, scoped access to Cloudflare — with
credential validation on the ZenML server, resource discovery, and rotation.

It serves two distinct planes:

* **Cloudflare R2** — the S3-compatible object storage data plane, consumed by the
  [Cloudflare R2 Artifact Store](../../artifact-stores/cloudflare-r2.md).
* **The Cloudflare account API** — the control plane, for components that call the
  Cloudflare REST API directly (Workers, Containers, Workflows, account
  management).

```shell
zenml service-connector list-types --type cloudflare
```

## Resource Types

The connector supports two resource types, each tied to the authentication method
that can actually serve it:

* `r2-bucket` — hands back a pre-configured, S3-compatible boto3 client scoped to a
  Cloudflare R2 bucket. R2's data plane is the S3 API, which requires SigV4
  signing, so this resource type is served by **R2 S3 credentials**. Resource IDs
  are R2 bucket URIs of the form `r2://{bucket-name}`. This is what the R2 Artifact
  Store links to.
* `cloudflare-generic` — hands back the account-scoped API token and account ID so
  consumers can build their own Cloudflare API clients for arbitrary services. The
  Cloudflare control plane uses a scoped bearer **API token**.

## Authentication Methods

* **Cloudflare API Token** (`api-token`) — a [scoped Cloudflare API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
  plus the account ID. Recommended for control-plane access. Apply least privilege
  by granting only the permissions the consuming component needs. Validated
  server-side against the Cloudflare `user/tokens/verify` endpoint. Serves the
  `cloudflare-generic` resource type.
* **R2 S3 Credentials** (`r2-credentials`) — an R2 [S3-compatible Access Key ID
  and Secret Access Key](https://developers.cloudflare.com/r2/api/tokens/) (generated
  from an R2 API token) plus the account ID. Serves the `r2-bucket` resource type.

The legacy global API key + email method is intentionally **not** supported, in
line with Cloudflare's least-privilege guidance.

{% hint style="info" %}
The connector derives the R2 S3 endpoint
(`https://<account_id>.r2.cloudflarestorage.com`) from the account ID, so you only
need to supply the account ID and credentials.
{% endhint %}

## Example: register a connector and link an R2 artifact store

Register a connector with R2 credentials:

```shell
zenml service-connector register cloudflare_r2 \
    --type cloudflare \
    --auth-method r2-credentials \
    --account_id=<CLOUDFLARE_ACCOUNT_ID> \
    --aws_access_key_id=<R2_ACCESS_KEY_ID> \
    --aws_secret_access_key=<R2_SECRET_ACCESS_KEY>
```

Discover the R2 buckets the connector can access:

```shell
zenml service-connector list-resources --resource-type r2-bucket
```

Register an R2 artifact store and connect it to the connector. The connector
brokers the credentials, while the artifact store supplies the R2 endpoint
(derived from its own `account_id`):

```shell
zenml artifact-store register cloudflare_store \
    --flavor=r2 \
    --path=r2://my-bucket/artifacts \
    --account_id=<CLOUDFLARE_ACCOUNT_ID>

zenml artifact-store connect cloudflare_store --connector cloudflare_r2
```

For control-plane access, register a connector with a scoped API token instead:

```shell
zenml service-connector register cloudflare_api \
    --type cloudflare \
    --auth-method api-token \
    --account_id=<CLOUDFLARE_ACCOUNT_ID> \
    --api_token=<CLOUDFLARE_API_TOKEN>
```

## A note on Cloudflare Sandbox bridge tokens

If you use a Cloudflare-backed sandbox, its bridge bearer token is **not** brokered
by this connector. A bridge token is a single static bearer to a Worker URL — it
is not Cloudflare account IAM, has no resource discovery, and does not fit the
broker model. It is configured as a secret directly on the sandbox flavor instead.
This mirrors how other third-party compute integrations (e.g. Modal, Lightning,
Databricks) handle their tokens, and keeps the connector focused on R2 and the
Cloudflare account API.
