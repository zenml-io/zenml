# CloudflareServiceConnector — design & scoping plan

This document records the scoping investigation and the answers to the five open
questions from the brief, **before** implementation. It also flags where the real
ZenML connector interface differs from assumptions.

## Scoping check result (Q1)

**Can an R2 bucket be brokered today by the existing AWS connector + S3 store?**
No — not end-to-end. Findings from the source:

- The AWS connector (`aws_service_connector.py`) *does* support a custom
  `endpoint_url` (`AWSBaseConfig.endpoint_url`, used at client construction in
  `_connect_to_resource` and `_verify`). Its `secret-key` auth method accepts a
  plain access-key-id + secret-access-key with no STS, which is what R2 issues.
- **But the endpoint is dropped on the consumer side.** When an S3 artifact store
  is *linked to a connector*, `S3ArtifactStore.get_credentials()` calls
  `connector.connect()` and extracts only `(access_key, secret_key, token,
  region)` from the returned boto3 client — it never reads the connector's
  `endpoint_url`. `S3ArtifactStore.filesystem` then rebuilds the filesystem from
  those four values plus `self.config.client_kwargs`. So the connector's R2
  endpoint is lost and requests would default to AWS S3.

Practical consequence for *our* components:
- Our `R2ArtifactStore` always carries the endpoint in `config.client_kwargs`
  (derived from `account_id`), and `S3ArtifactStore.filesystem` *does* merge
  `self.config.client_kwargs`. So a connector that hands our R2 store
  R2 S3 credentials works: **creds come from the connector, endpoint from the
  store config.** No core change to the S3 store is required for v1.
- Using the *AWS* connector for R2 is also semantically wrong UX (asks for AWS
  region/ARNs, lists AWS buckets, surfaces as "AWS").

**Verdict:** A dedicated Cloudflare connector earns its place. The unique value
over "S3 store with direct credentials" is: centralized credential management +
**rotation**, Cloudflare-native **resource discovery** (list R2 buckets), and a
correct Cloudflare-branded UX. `r2-bucket` survives the scoping check.

## Resource types & auth methods (Q2)

Two resource types, each tied to the auth method that can actually serve it:

| Resource type        | `supports_instances` | Auth method      | `_connect_to_resource` returns |
|----------------------|----------------------|------------------|--------------------------------|
| `cloudflare-generic` | False                | `api-token`      | credentials object (token + account_id) — modeled on `azure-generic` |
| `r2-bucket`          | True                 | `r2-credentials` | a boto3 S3 client pointed at the R2 endpoint, with `.credentials` attached (mirrors AWS `s3-bucket`) |

Rationale for the split:
- R2's **data plane** (object get/put, ListBuckets, HeadBucket) is the S3 API and
  requires SigV4 with an access-key-id/secret — a bearer API token cannot sign S3
  requests. So `r2-bucket` only accepts `r2-credentials`.
- The Cloudflare **control plane** (account/Workers/Containers/Workflows API) uses
  a scoped bearer API token. So `cloudflare-generic` only accepts `api-token`.

R2's S3 API implements `ListBuckets`/`HeadBucket`, so bucket **discovery for
`r2-bucket` uses boto3 against the R2 endpoint** — a direct mirror of the AWS
connector's `list_buckets()`/`head_bucket()`. No Cloudflare REST API or extra SDK
is needed for the R2 path.

Auth methods shipped in v1:
- `api-token` — scoped Cloudflare API token + `account_id`. Primary; control plane.
- `r2-credentials` — `aws_access_key_id` + `aws_secret_access_key` + `account_id`.
  (Field names kept S3-shaped so the boto3 session reads naturally.)

**Omitted:** `api-key` (global key + email). It is legacy and discouraged by
Cloudflare and violates least-privilege; not worth the surface area in v1.

Dependencies: `boto3` (already an integration requirement) for the R2 path;
`requests` (ZenML core dep) for verifying the API token against
`https://api.cloudflare.com/client/v4/user/tokens/verify`. No `cloudflare` SDK
dependency added.

## Bridge token stays out of the connector (Q3)

**Confirmed out.** The sandbox bridge token is a single static bearer to a Worker
URL — it is not Cloudflare account IAM, has no resource discovery, and doesn't fit
the broker model. It stays a `SecretField` on the sandbox flavor. This also keeps
the connector from being a dependency of the sandbox flavor's v1.

## Resource discovery under token scoping (Q4)

- `r2-bucket`, no resource_id → `s3_client.list_buckets()` against the R2 endpoint;
  returns `r2://<name>` for each visible bucket. R2 tokens scoped to specific
  buckets only return those, which is the desired least-privilege behavior.
- `r2-bucket`, with resource_id → `s3_client.head_bucket(Bucket=name)`; returns the
  canonical id or raises `AuthorizationException`.
- `cloudflare-generic` → verify the token via the Cloudflare `tokens/verify`
  endpoint; returns the single generic resource id (the `account_id`).
- Canonical id for `r2-bucket`: strip `r2://`/`s3://` prefixes to the bare bucket
  name internally, surface as `r2://<bucket>` (mirrors AWS `_parse_s3_resource_id`
  + `_canonical_resource_id`).

## Precedent: third-party compute tokens (Q5)

Survey of compute integrations:
- **Modal**: no connector, no SecretField — pure ambient auth via the Modal SDK.
- **Lightning, Databricks**: `SecretField` on the flavor, no connector.
- **Run:AI, SkyPilot**: ambient/implicit, no connector.
- **HyperAI**: the *only* compute integration with a connector — and only because
  it brokers SSH key infrastructure (multi-key, multi-host), a true IAM-shaped
  problem.

**Conclusion:** the norm for a token to a third-party compute service is a
`SecretField`, not a connector. This corroborates Q3: the sandbox flavor does not
need this connector, and the connector's justification rests entirely on R2 (data
plane brokering + discovery + rotation) and Cloudflare account API access — not on
sandboxes.

## Interface notes / deltas from the brief

- Custom connectors implement (on `ServiceConnector`): `_get_connector_type`
  (classmethod returning a `ServiceConnectorTypeModel`), `_connect_to_resource`,
  `_configure_local_client`, `_auto_configure` (classmethod), `_verify`, and
  optionally `_canonical_resource_id` / `_get_default_resource_id` /
  `_get_connector_client`. The `config` field is typed to an
  `AuthenticationConfig` subclass. Registration is automatic via
  `ServiceConnectorMeta` once the class is imported.
- Type declaration uses `ServiceConnectorTypeModel` + `ResourceTypeModel` +
  `AuthenticationMethodModel`; auth credential schemas attach via
  `config_class=<AuthenticationConfig subclass>`.
- The integration must (a) import its `service_connectors` module in
  `CloudflareIntegration.activate()` to trigger metaclass registration, and
  (b) be added to `register_builtin_service_connectors()` so the type shows up in
  `zenml service-connector list-types` even before the stack touches it.
- `_configure_local_client`: for `r2-bucket` we can write an AWS profile pointing
  at the R2 endpoint (reusing the aws-profile-manager helper is AWS-specific);
  v1 will raise `NotImplementedError` for local client config to avoid scope
  creep, matching how several connectors handle unsupported local config.

## Deliverables for this workstream

1. `service_connectors/cloudflare_service_connector.py` — spec + config classes +
   connector implementation.
2. `service_connectors/__init__.py`; wire `activate()` + constants in the
   integration `__init__.py`; add to `register_builtin_service_connectors()`.
3. `R2ArtifactStoreFlavor.service_connector_requirements` →
   `connector_type="cloudflare", resource_type="r2-bucket", resource_id_attr="path"`.
4. Unit tests mirroring AWS connector coverage (mocked boto3 + mocked `requests`).
5. Docs page for the connector.
