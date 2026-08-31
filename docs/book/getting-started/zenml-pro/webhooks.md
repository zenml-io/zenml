---
description: Receive authenticated events from external systems in ZenML.
icon: webhook
---

# Webhooks

Webhooks connect external systems to ZenML so that your ZenML deployment can
react to events that happen outside the platform. For example, you can receive
an event when a pull request is merged in GitHub, when a GitHub Actions workflow
finishes, or when an internal service publishes a new model version.

When you create a webhook, ZenML exposes a project-scoped intake URL. Configure
the external system to send signed HTTP requests to that URL.

For every delivery, the webhook endpoint:

1. verifies the request signature using the webhook's signing secret;
2. validates the headers and JSON payload required by that webhook type;
3. records intake statistics for accepted and rejected deliveries; and
4. makes an accepted event available to configured consumers.

Consumers define how ZenML reacts to accepted events. For example, a
[webhook trigger](triggers.md#webhook-triggers) can filter GitHub events and
execute attached pipeline snapshots when a pull request is merged or a branch
is pushed.

The endpoint returns an HTTP response to the sender. A valid delivery normally
returns `202 Accepted`; an invalid signature, invalid payload, missing webhook,
or inactive webhook returns an appropriate `4xx` response. The response reports
the result of webhook intake. Any work performed by consumers happens after
that intake decision.

## Available providers

| Provider | Type | Authentication | Event model |
|----------|------|----------------|-------------|
| [GitHub](webhooks/github.md) | `github` | GitHub HMAC-SHA256 signature | Curated semantic GitHub events and string filters |
| [Custom webhooks](webhooks/custom.md) | `custom` | ZenML HMAC-SHA256 signature | User-supplied event name and JSON object |

Provider pages describe the headers, event model, external setup, and manual
testing procedure for each provider.

## Manage webhooks

Webhooks are project-scoped resources. Their basic lifecycle is create,
inspect, update, and delete.

### Create a webhook

Choose a name and provider type to create a webhook in the active project:

```bash
zenml webhook create my-github-webhook --type github
```

The equivalent SDK flow is:

```python
from zenml.client import Client
from zenml.enums import WebhookType

client = Client()
result = client.create_webhook(
    name="my-github-webhook",
    webhook_type=WebhookType.GITHUB,
)

webhook = result.webhook
print(webhook.endpoint_url)
```

The provider type determines how deliveries are authenticated and interpreted
and cannot be changed after creation. By default, ZenML also generates a
signing secret. Capture it as described in
[Manage signing credentials](#manage-signing-credentials).

### Describe and list webhooks

Describe one webhook by name or ID, or list the webhooks in the active project:

```bash
zenml webhook describe my-github-webhook
zenml webhook list
```

`describe` includes the complete endpoint URL. Use that value when configuring
the external provider instead of constructing the URL manually.

With the SDK, `get_webhook` accepts a name, ID, or ID prefix. `list_webhooks`
supports filters such as provider type and active state:

```python
from zenml.client import Client
from zenml.enums import WebhookType

client = Client()

webhook = client.get_webhook("my-github-webhook")
github_webhooks = client.list_webhooks(
    webhook_type=WebhookType.GITHUB,
    active=True,
)
```

Normal describe, get, and list responses never include the signing secret.

### Update a webhook

You can rename a webhook or change its active state. These are the only mutable
webhook properties:

```bash
zenml webhook update my-github-webhook --name production-github
zenml webhook update production-github --inactive
zenml webhook update production-github --active
```

Via the SDK:

```python
webhook = client.update_webhook(
    name_id_or_prefix="my-github-webhook",
    name="production-github",
    active=False,
)
```

The webhook ID, project association, and provider type cannot be updated. The
endpoint path is derived from the provider type and webhook ID. An inactive
webhook rejects otherwise valid deliveries with `409 Conflict`. Changing the
webhook's active state does not change the active state or configuration of its
consumers.

### Delete a webhook

Delete a webhook by name or ID:

```bash
zenml webhook delete production-github
```

Via the SDK:

```python
client.delete_webhook("production-github")
```

ZenML rejects deletion while a non-archived webhook trigger references the
webhook. Archive or permanently delete those triggers before deleting the
webhook. Archived trigger history and its serialized configuration are retained.

## Manage signing credentials

Every webhook has one active signing secret. The sender uses it to sign the
exact request body, and ZenML uses it to authenticate the delivery. The secret
is write-only after it is created or rotated: normal webhook responses never
expose it.

Secret visibility depends on the operation:

| Operation | CLI behavior | SDK behavior |
|-----------|--------------|--------------|
| Create with a generated secret | Prints the secret once | Returns it once as `result.secret` |
| Create with a user-supplied secret | Does not print the secret | `result.secret` is `None` |
| Rotate to a generated secret | Prints the replacement once | Returns it once as `result.secret` |
| Rotate to a user-supplied secret | Prints the active replacement | Returns it once as `result.secret` |
| Describe, get, or list | Never exposes the secret | Never exposes the secret |

### Use a ZenML-generated secret

When you omit `--secret`, ZenML generates a secret and the CLI prints it once as
part of the create command:

```bash
zenml webhook create my-github-webhook --type github
```

Store the printed value securely before leaving the command output. With the
SDK, the generated secret is available only on the create result:

```python
result = client.create_webhook(
    name="my-github-webhook",
    webhook_type=WebhookType.GITHUB,
)
signing_secret = result.secret.get_secret_value()
```

Subsequent calls to `get_webhook` or `list_webhooks` do not return it.

### Provide your own secret

If an existing credential-management workflow needs to choose the value, pass
it during creation:

```bash
zenml webhook create my-github-webhook \
  --type github \
  --secret "$WEBHOOK_SECRET"
```

Via the SDK:

```python
import os

webhook_secret = os.environ["WEBHOOK_SECRET"]
result = client.create_webhook(
    name="my-github-webhook",
    webhook_type=WebhookType.GITHUB,
    secret=webhook_secret,
)
```

ZenML does not echo a user-supplied secret. The CLI does not print it, and
`result.secret` is `None` in the SDK.

### Rotate a signing secret

Generate a replacement signing secret with:

```bash
zenml webhook rotate-secret my-github-webhook
```

Or provide the replacement yourself:

```bash
zenml webhook rotate-secret my-github-webhook \
  --secret "$NEW_WEBHOOK_SECRET"
```

Via the SDK:

```python
import os

result = client.rotate_webhook_secret("my-github-webhook")
new_secret = result.secret.get_secret_value()

replacement_secret = os.environ["NEW_WEBHOOK_SECRET"]
result = client.rotate_webhook_secret(
    "my-github-webhook",
    secret=replacement_secret,
)
```

The replacement secret is returned once. The previous secret stops
authenticating deliveries as soon as rotation completes, so update the external
provider with the replacement to resume delivery.

{% hint style="warning" %}
Treat signing secrets as credentials. Do not commit them to source control,
include literal values in command history, or log them in production.
{% endhint %}

## Understand delivery responses

Webhook endpoints return intake-level responses:

| Status | Meaning |
|--------|---------|
| `202 Accepted` | The delivery was accepted for processing, or the provider intentionally ignored an unsupported event before webhook lookup. |
| `400 Bad Request` | Required provider metadata is missing, or the body is not a valid top-level JSON object. |
| `401 Unauthorized` | The signature does not match the exact request body. |
| `404 Not Found` | The webhook does not exist, or the provider in the URL does not match its stored type. |
| `409 Conflict` | The authenticated webhook is inactive. |

For signed requests, the sender and ZenML must calculate the signature over the
same raw bytes. Reformatting JSON or adding a trailing newline after calculating
the signature changes those bytes and causes authentication to fail.

Provider-specific early handling can refine this behavior. For example, GitHub
deliveries with a non-empty but unsupported `X-GitHub-Event` value return `202`
without resolving a webhook. See the [GitHub provider](webhooks/github.md) for
details.

## Inspect intake statistics

Hydrated webhook details include intake statistics that help answer whether a
provider is reaching and authenticating with ZenML:

- received, accepted, authentication-failed, and invalid-payload counts;
- the last received and accepted timestamps;
- the last error timestamp and a bounded error summary.

The CLI `describe` command and the SDK `get_webhook` method return hydrated
details by default:

```bash
zenml webhook describe my-github-webhook
```

```python
webhook = client.get_webhook("my-github-webhook")
print(webhook.stats.accepted_count)
print(webhook.stats.auth_failed_count)
print(webhook.stats.last_error_summary)
```

These statistics cover intake only. They do not report consumer matches, queue
publication, pipeline run creation, or run outcomes.

## Next steps

- [Configure a GitHub webhook](webhooks/github.md)
- [Send custom webhook events](webhooks/custom.md)
- [Execute snapshots with webhook triggers](triggers.md#webhook-triggers)
