---
description: Configure and test ClickUp webhook delivery to ZenML.
---

# ClickUp webhooks

The ClickUp webhook provider authenticates Workspace webhook deliveries and
maps supported ClickUp payloads to a small catalog of semantic events. Consumers
can use this provider-owned event model instead of depending on ClickUp's raw
payload structure. [Webhook triggers](../triggers.md#webhook-triggers) are the
currently documented consumer that exposes this event configuration.

ClickUp registers webhooks through its API and generates the signing secret
itself. Create the ZenML webhook first so you have an intake URL, then store
ClickUp's secret on the ZenML webhook.

## Create the webhook in ZenML

Create a ClickUp webhook in the active project:

```bash
zenml webhook create clickup-ops --type clickup
```

Describe the webhook and copy its endpoint URL:

```bash
zenml webhook describe clickup-ops
```

Via the SDK:

```python
from zenml.client import Client
from zenml.webhooks.providers import BuiltinWebhookType

client = Client()
result = client.create_webhook(
    name="clickup-ops",
    webhook_type=BuiltinWebhookType.CLICKUP,
)

endpoint_url = result.endpoint_url
```

You can ignore the generated ZenML secret. ClickUp will issue a different
shared secret when you register the endpoint, and that is the value ZenML must
verify. See [Create a webhook](../webhooks.md#create-a-webhook) for
secret-management and rotation options.

## Register the webhook in ClickUp

ClickUp does not provide a repository-style webhook settings page. Create the
subscription with the [Create Webhook](https://developer.clickup.com/reference/createwebhook)
API using a personal API token and your Workspace ID (`team_id`).

1. In ClickUp, open **Settings** > **Apps** and create a personal API token.
2. Copy the Workspace ID for the Workspace that should send events.
3. Send a `POST` request that points ClickUp at the ZenML endpoint URL.

```bash
export CLICKUP_TOKEN="<personal-api-token>"
export CLICKUP_TEAM_ID="<workspace-id>"
export WEBHOOK_URL="<endpoint-url-from-zenml>"

curl -s -X POST "https://api.clickup.com/api/v2/team/${CLICKUP_TEAM_ID}/webhook" \
  -H "Authorization: $CLICKUP_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"endpoint\": \"$WEBHOOK_URL\",
    \"events\": [
      \"taskCreated\",
      \"taskUpdated\",
      \"taskDeleted\",
      \"taskStatusUpdated\",
      \"taskMoved\",
      \"taskAssigneeUpdated\",
      \"taskCommentPosted\",
      \"listCreated\",
      \"listUpdated\",
      \"listDeleted\"
    ]
  }"
```

Copy `webhook.secret` from the response. You can optionally include `space_id`,
`folder_id`, `list_id`, or `task_id` so ClickUp only sends events from one
location. ZenML trigger filters still apply to whatever ClickUp delivers.

ClickUp sends an `X-Signature` header containing a raw hexadecimal HMAC-SHA256
digest of the exact request body. There is no `sha256=` prefix. ZenML verifies
this signature before it parses or forwards the delivery.

## Store ClickUp's signing secret

Rotate the ZenML webhook secret to the value ClickUp returned. Until this step
succeeds, real ClickUp deliveries fail authentication with `401 Unauthorized`.
ClickUp [suspends the webhook](https://developer.clickup.com/docs/webhookhealth)
after that response.

```bash
zenml webhook rotate-secret clickup-ops --secret "$CLICKUP_WEBHOOK_SECRET"
```

Via the SDK:

```python
import os

client.rotate_webhook_secret(
    "clickup-ops",
    secret=os.environ["CLICKUP_WEBHOOK_SECRET"],
)
```

## Supported events and filters

The provider reads the ClickUp event name from the JSON `event` field and maps
qualifying payloads to ZenML semantic events with the same names:

| ClickUp event | ZenML semantic event | Available filter fields |
|---------------|----------------------|------------------------|
| Task created | `taskCreated` | `task_id`, `list_id`, `space_id`, `folder_id` |
| Task updated | `taskUpdated` | `task_id`, `list_id`, `space_id`, `folder_id` |
| Task deleted | `taskDeleted` | `task_id`, `list_id`, `space_id`, `folder_id` |
| Task status updated | `taskStatusUpdated` | `task_id`, `list_id`, `space_id`, `folder_id`, `status` |
| Task moved | `taskMoved` | `task_id`, `list_id`, `space_id`, `folder_id` |
| Task assignee updated | `taskAssigneeUpdated` | `task_id`, `list_id`, `space_id`, `folder_id` |
| Task comment posted | `taskCommentPosted` | `task_id`, `list_id`, `space_id`, `folder_id` |
| List created | `listCreated` | `list_id`, `space_id`, `folder_id` |
| List updated | `listUpdated` | `list_id`, `space_id`, `folder_id` |
| List deleted | `listDeleted` | `list_id`, `space_id`, `folder_id` |

Event names match ClickUp's camelCase identifiers. Resource IDs are compared
as strings, even when ClickUp sends a numeric `list_id`, `space_id`, or
`folder_id`.

`status` is the post-change value from the last `history_items` entry: a
string `after` value, or `after.status` when `after` is an object. It is
typically present for `taskStatusUpdated`. If you filter on `status` and the
payload has no after-value, the event does not match.

A ClickUp event that is missing from this catalog can still authenticate and
return `202 Accepted`. It is not mapped to a semantic event, so webhook
triggers do not match it. A missing or empty `event` or `webhook_id` field
returns `400 Bad Request`.

### String filters

Semantic event fields use ZenML string filters (`StringFilterOption`). You can
use:

- a plain string for exact equality, such as `list_id: "162641285"`;
- `oneof:` with a non-empty JSON list for exact alternatives, such as
  `status: 'oneof:["done","complete"]'`.

ClickUp ID and status fields do not support `startswith:`. Values configured for
the same field use OR logic; different populated fields use AND logic. Omitted
fields match any value. If a configured field is absent from a delivery, it
does not match.

For example, this target matches status updates to `done` on one list:

```yaml
target_events:
  - type: taskStatusUpdated
    list_id: "162641285"
    status: done
```

See [Webhook triggers](../triggers.md#clickup-webhook-triggers) for a complete
example that uses this configuration to execute a pipeline snapshot.

## Mock a signed ClickUp delivery

You can test the endpoint without asking ClickUp to send a delivery. This
example uses a minimal ClickUp-like status payload; the important part is
signing and sending exactly the same bytes.

Set the endpoint and the ClickUp signing secret stored on the ZenML webhook:

```bash
export WEBHOOK_URL="<endpoint-url-from-zenml>"
export WEBHOOK_SECRET="<clickup-webhook-secret>"
```

Write the request body without adding a trailing newline:

```bash
printf '%s' '{"event":"taskStatusUpdated","webhook_id":"wh-1","task_id":"abc","list_id":"162641285","history_items":[{"id":"hist-1","after":"done"}]}' > clickup-status.json
```

Calculate the raw hexadecimal signature over the file's exact bytes:

```bash
export SIGNATURE="$(python -c 'import hashlib,hmac,os; body=open("clickup-status.json","rb").read(); print(hmac.new(os.environ["WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest())')"
```

Send those same bytes with the ClickUp signature header:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  --data-binary @clickup-status.json
```

A valid delivery returns `202 Accepted`. This confirms webhook intake, not that
a consumer matched or a pipeline run started.

To confirm that signature verification is active, send the same body with an
invalid signature:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid" \
  --data-binary @clickup-status.json
```

This request returns `401 Unauthorized`. If a calculated signature fails,
verify that the bytes passed to `--data-binary` are the bytes used to calculate
the digest; even a whitespace or newline change produces a different signature.
Do not prefix the digest with `sha256=`.

ClickUp [immediately suspends](https://developer.clickup.com/docs/webhookhealth)
a webhook after an unauthorized response, so align the signing secret before
ClickUp starts delivering events.

## Related pages

- [Webhooks](../webhooks.md)
- [GitHub webhooks](github.md)
- [Custom webhooks](custom.md)
- [Webhook triggers](../triggers.md#clickup-webhook-triggers)
