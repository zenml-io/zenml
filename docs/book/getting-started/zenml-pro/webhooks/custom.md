---
description: Send signed custom events to a ZenML webhook.
---

# Custom webhooks

The custom webhook provider is a provider-neutral way to send signed JSON
events to ZenML. Use it when a service can make HTTP requests but does not have
a dedicated ZenML webhook provider.

Custom webhooks preserve the sender's event name and JSON payload for consumers.
They do not define a ZenML semantic event catalog. A
[custom webhook trigger](../triggers.md#custom-webhook-triggers) can retain the
original match-all behavior with an empty configuration or use a
[dynamic event filter](../triggers.md#dynamic-event-filters) to match the event
name and fields in the authenticated JSON body.

## Create a custom webhook

Create the webhook and copy the generated signing secret:

```bash
zenml webhook create custom-events --type custom
zenml webhook describe custom-events
```

Via the SDK:

```python
from zenml.client import Client
from zenml.webhooks.providers import BuiltinWebhookType

client = Client()
result = client.create_webhook(
    name="custom-events",
    webhook_type=BuiltinWebhookType.CUSTOM,
)

endpoint_url = result.endpoint_url
signing_secret = result.secret.get_secret_value()
```

See [Create a webhook](../webhooks.md#create-a-webhook) for lifecycle and
secret-management options shared by all providers.

## Delivery contract

Send an HTTP `POST` request whose body is a valid JSON object. The custom
provider reads these headers:

| Header | Required | Meaning |
|--------|----------|---------|
| `X-ZenML-Signature-256` | Yes | `sha256=<hex_digest>` calculated with HMAC-SHA256 over the exact request body |
| `X-ZenML-Event` | Yes | The sender-defined event name made available to consumers |
| `X-ZenML-Delivery` | No | A sender-defined delivery identifier for observability |

The payload must contain a JSON object at the top level. JSON arrays, scalar
values, and malformed JSON return `400 Bad Request`.

## Send a signed event

Set the endpoint and secret captured during creation:

```bash
export WEBHOOK_URL="<endpoint-url-from-zenml>"
export WEBHOOK_SECRET="<signing-secret>"
```

Write the body, calculate its signature with Python, and send the same bytes
with `curl`:

```bash
printf '%s' '{"model":"fraud-detector","version":"2026.08.31"}' > custom-event.json

export SIGNATURE="$(python -c 'import hashlib,hmac,os; body=open("custom-event.json","rb").read(); print("sha256=" + hmac.new(os.environ["WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest())')"

curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-ZenML-Event: model.published" \
  -H "X-ZenML-Delivery: manual-delivery-001" \
  -H "X-ZenML-Signature-256: $SIGNATURE" \
  --data-binary @custom-event.json
```

A valid delivery returns `202 Accepted`. The event name and parsed JSON object
are then available to configured consumers. This response does not promise that
a consumer matched or completed its work.

If authentication fails, verify that the sent body is byte-for-byte identical
to the body used to calculate the signature. See
[Understand delivery responses](../webhooks.md#understand-delivery-responses)
for the shared response contract.

## Related pages

- [Webhooks](../webhooks.md)
- [Slack webhooks](slack.md)
- [GitHub webhooks](github.md)
- [ClickUp webhooks](clickup.md)
- [Custom webhook triggers](../triggers.md#custom-webhook-triggers)
