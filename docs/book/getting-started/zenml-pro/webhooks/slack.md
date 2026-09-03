---
description: Connect the Slack Events API to a ZenML webhook endpoint.
---

# Slack webhooks

The Slack webhook provider receives and authenticates callbacks from the Slack
Events API. Use it to verify a Slack app's Request URL and turn selected Slack
collaboration events into ZenML automation triggers.

This inbound provider is separate from the
[Slack alerter](../../../component-guide/alerters/slack.md). The alerter uses a
Slack OAuth token to send messages from a pipeline; the webhook provider uses
the Slack app's signing secret to authenticate callbacks sent to ZenML.

## Create a Slack webhook

Create a [Slack app](https://api.slack.com/apps) in the workspace you want to
connect. A free Slack workspace is sufficient. In the app configuration, open
**Basic Information**, find **App Credentials**, and copy the **Signing
Secret**.

Pass that Slack-owned secret when creating the ZenML webhook:

```bash
export SLACK_SIGNING_SECRET="<signing-secret-from-slack>"

zenml webhook create slack-events \
  --type slack \
  --secret "$SLACK_SIGNING_SECRET"
```

Then describe the webhook and copy its endpoint URL:

```bash
zenml webhook describe slack-events
```

Via the SDK:

```python
import os

from zenml.client import Client
from zenml.webhooks.providers import BuiltinWebhookType

result = Client().create_webhook(
    name="slack-events",
    webhook_type=BuiltinWebhookType.SLACK,
    secret=os.environ["SLACK_SIGNING_SECRET"],
)

endpoint_url = result.endpoint_url
```

ZenML still permits omission of `--secret` and will generate a value as it does
for other providers. That generated value cannot authenticate Slack callbacks:
Slack owns the signing secret used for this integration.

## Verify the Events API Request URL

Your ZenML endpoint must be reachable from Slack over public HTTPS.
Slack **Socket Mode must be disabled**: Socket Mode delivers Events API
callbacks over a WebSocket connection instead of sending them to the ZenML
HTTP endpoint.

1. In the Slack app configuration, open **Event Subscriptions**.
2. Turn on **Enable Events**.
3. Paste the ZenML webhook endpoint into **Request URL**.
4. Wait for Slack to show **Verified**.

Slack sends a signed `url_verification` delivery during this flow. ZenML first
verifies the Slack signature and timestamp, then returns the challenge as
`200 OK` plaintext. The control delivery increments accepted intake statistics
but does not create a `WebhookEvent`.

If verification fails, check that:

- the endpoint is publicly reachable over HTTPS;
- **Socket Mode** is disabled;
- the ZenML webhook was created with this Slack app's signing secret; and
- the server clock is accurate enough for Slack's five-minute request window.

If URL verification succeeds but subscribed events do not increment the
webhook's `received_count`, also confirm that Socket Mode remains disabled, the
app was reinstalled after its scopes changed, and the app belongs to the test
channel.

## Subscribe to automation events

Slack controls which callbacks reach ZenML through the app's
[event subscriptions](https://docs.slack.dev/apis/events-api/), OAuth scopes,
and channel visibility. Under **Subscribe to bot events**, add only the source
events needed by your automations:

| Slack bot event subscription | ZenML semantic event | Required bot scope |
|------------------------------|----------------------|--------------------|
| `app_mention` | `app_mention` | `app_mentions:read` |
| `message.channels` | `message_posted` in public channels | `channels:history` |
| `message.groups` | `message_posted` in private channels | `groups:history` |
| `message.im` | `message_posted` in direct messages | `im:history` |
| `message.mpim` | `message_posted` in group direct messages | `mpim:history` |
| `reaction_added` | `reaction_added` | `reactions:read` |
| `reaction_removed` | `reaction_removed` | `reactions:read` |
| `message_metadata_posted` | `message_metadata_posted` | `metadata.message:read` |
| `message_metadata_updated` | `message_metadata_updated` | `metadata.message:read` |
| `file_shared` | `file_shared` | `files:read` |

The four Slack message subscriptions all arrive with the raw inner event type
`message`. ZenML exposes qualifying messages as the more precise semantic event
`message_posted`.

Message-metadata subscriptions have one additional source-side control. In the
app manifest, add `settings.event_subscriptions.metadata_subscriptions` entries
that select an `app_id` and metadata `event_type`. Slack permits one of those
values, but not both, to be `*`; prefer explicit values when possible. See
Slack's [message metadata documentation](https://docs.slack.dev/messaging/message-metadata/)
for the manifest format.

Install or reinstall the app when Slack asks you to apply scope changes. Invite
the app to any channel from which it should receive events, then perform one of
the subscribed actions.

An authenticated `event_callback` returns an empty `200 OK`. ZenML maps the
inner Slack event's `type` to `WebhookEvent.event_type`, maps Slack's `event_id`
to `WebhookEvent.delivery_id`, and preserves the complete outer payload. Event
handlers run in an in-process background task after the HTTP response is sent.

Slack's subscriptions are the source-side filter: they determine which event
families and visible conversations Slack sends. ZenML event filters are the
destination-side control: they select which accepted callbacks launch a given
automation. The Events API does not provide arbitrary source-side filters for
message text, sender, channel, reaction name, or file ID.

## Supported events and filters

ZenML supports the following curated automation events. Every filter field is
optional; populated fields on one event filter combine with AND. Every
normalized event includes `type`, `event_id`, `team_id`, `channel_id`,
`user_id`, `event_time`, and `event_ts`; fields unavailable in a particular
Slack callback are `null`.

| Event filter `type` | Destination filter fields | Additional normalized event fields |
|---------------------|---------------------------|------------------------------------|
| `app_mention` | `team_id`, `channel_id`, `user_id`, `threaded` | `message_ts`, `thread_ts` |
| `message_posted` | `team_id`, `channel_id`, `user_id`, `channel_type`, `text`, `threaded` | `channel_type`, `text`, `message_ts`, `thread_ts` |
| `reaction_added` | `team_id`, `channel_id`, `reaction`, `user_id`, `item_user_id`, `item_type`, `item_id` | `reaction`, `item_user_id`, `item` (`type`, `id`, `channel_id`, `file_id`) |
| `reaction_removed` | `team_id`, `channel_id`, `reaction`, `user_id`, `item_user_id`, `item_type`, `item_id` | `reaction`, `item_user_id`, `item` (`type`, `id`, `channel_id`, `file_id`) |
| `message_metadata_posted` | `team_id`, `channel_id`, `app_id`, `user_id`, `bot_id`, `metadata_event_type` | `app_id`, `bot_id`, `message_ts`, `metadata` (`event_type`, `event_payload`) |
| `message_metadata_updated` | `team_id`, `channel_id`, `app_id`, `user_id`, `bot_id`, `metadata_event_type` | `app_id`, `bot_id`, `message_ts`, `metadata`, `previous_metadata` |
| `file_shared` | `team_id`, `channel_id`, `user_id`, `file_id` | `file_id` |

String filters support exact values, YAML lists, and the `oneof:` expression.
`text` and `metadata_event_type` additionally support `startswith:`. Prefix
matching is intentionally unavailable for opaque Slack IDs, reaction names,
channel types, and reaction item types. `threaded` is a boolean filter.

ZenML applies a few semantic qualifications and normalizations:

- `message_posted` accepts only ordinary human-authored messages. Message
  subtypes, bot messages, and malformed messages are ignored. Root messages and
  thread replies can be selected with `threaded`.
- Reactions can reference a `message`, `file`, or `file_comment`. `item_type`
  selects `item.type`, and `item_id` selects `item.id`. The normalized ID is
  respectively the message timestamp, file ID, or file-comment ID.
  `channel_id` is only present when Slack includes it.
- Message-metadata events expose the metadata's declared event type for
  filtering. The complete metadata payload, and the previous metadata on
  updates, remain in the normalized event but are not JSON-path filters.
- `file_shared` exposes the IDs delivered by Slack. ZenML does not call Slack's
  Web API to enrich the file during intake.

Other valid Slack event callbacks can still be accepted by intake, but they do
not match a trigger.

## Create a Slack trigger

Slack trigger configuration follows the same typed `target_events` shape as
other filtered webhook providers. Multiple event filters combine with OR. Create
`slack-automation.yaml`:

```yaml
target_events:
  - type: app_mention
    channel_id: C0123456789
    threaded: false
  - type: message_posted
    channel_id: C0123456789
    text: "startswith:deploy production"
  - type: reaction_added
    channel_id: C0123456789
    reaction: rocket
    item_type: message
  - type: message_metadata_posted
    metadata_event_type: "startswith:zenml.pipeline."
```

Create the trigger for the Slack webhook:

```bash
zenml trigger webhook create on-slack-automation \
  --webhook slack-events \
  --config slack-automation.yaml
```

Via the SDK, use the typed Slack configuration:

```python
from zenml.client import Client
from zenml.webhooks.providers.slack import (
    AppMentionEventFilter,
    MessagePostedEventFilter,
    ReactionAddedEventFilter,
    SlackWebhookConfiguration,
)

client = Client()
trigger = client.create_webhook_trigger(
    name="on-slack-automation",
    webhook="slack-events",
    configuration=SlackWebhookConfiguration(
        target_events=[
            AppMentionEventFilter(
                channel_id="C0123456789",
                threaded=False,
            ),
            MessagePostedEventFilter(
                channel_id="C0123456789",
                text="startswith:deploy production",
            ),
            ReactionAddedEventFilter(
                channel_id="C0123456789",
                reaction="rocket",
                item_type="message",
            ),
        ]
    ),
)
```

Attach the trigger to a pipeline snapshot before testing it. See
[Webhook triggers](../triggers.md#webhook-triggers) for attachment and runtime
inspection commands.

The normalized events retain useful non-filterable context such as Slack's
`event_id`, event timestamp, message timestamp, thread timestamp, and metadata
payload. ZenML does not call Slack to resolve message permalinks during intake
or matching.

## Authentication and accepted envelopes

Slack signs the exact raw request body with the app signing secret. ZenML
requires `X-Slack-Signature` with the `v0=` version and
`X-Slack-Request-Timestamp`, rejects timestamps more than five minutes from the
server time, and compares signatures in constant time. The implementation
follows Slack's
[request-signing procedure](https://docs.slack.dev/authentication/verifying-requests-from-slack/).

The provider accepts these top-level envelopes:

| Slack delivery type | ZenML behavior |
|---------------------|----------------|
| `event_callback` | Returns empty `200` and schedules one trusted `WebhookEvent` |
| `url_verification` | Returns `200 text/plain` with the challenge and schedules no event |
| `app_rate_limited` | Returns empty `200` and schedules no event |

Malformed JSON, malformed known envelopes, and unsupported top-level delivery
types return `400 Bad Request`. For `app_rate_limited`, ZenML validates Slack's
`team_id`, `api_app_id`, and integer `minute_rate_limited` fields before
acknowledging the control delivery. Missing, invalid, stale, or future-dated
authentication metadata returns `401 Unauthorized`.

Slack may retry deliveries. The current intake path does not provide
cross-delivery idempotency or a durable handoff to background handlers.

## Mock a signed Slack message

You can test the endpoint without asking Slack to send a delivery. This example
uses a minimal Slack-like `message` callback and computes the `v0` signature
over Slack's timestamp-prefixed signature base.

Set the endpoint and the Slack signing secret used when you created the
webhook:

```bash
export WEBHOOK_URL="<endpoint-url-from-zenml>"
export WEBHOOK_SECRET="<slack-signing-secret>"
export SLACK_TIMESTAMP="$(date +%s)"
```

Write the body without adding a trailing newline:

```bash
printf '%s' '{"type":"event_callback","team_id":"T0123456789","event":{"type":"message","channel":"C0123456789","channel_type":"channel","user":"U0123456789","text":"deploy production","ts":"1788300000.000100","event_ts":"1788300000.000100"},"event_id":"Ev0123456789","event_time":1788300000}' > slack-message.json
```

Calculate the signature over the exact body bytes and current timestamp:

```bash
export SIGNATURE="$(python -c 'import hashlib,hmac,os; body=open("slack-message.json","rb").read(); timestamp=os.environ["SLACK_TIMESTAMP"]; base=f"v0:{timestamp}:".encode()+body; print("v0="+hmac.new(os.environ["WEBHOOK_SECRET"].encode(),base,hashlib.sha256).hexdigest())')"
```

Send those same bytes with the Slack authentication headers:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Slack-Request-Timestamp: $SLACK_TIMESTAMP" \
  -H "X-Slack-Signature: $SIGNATURE" \
  --data-binary @slack-message.json
```

A valid delivery returns `200 OK`. This confirms webhook intake, not that a
trigger matched or a pipeline run started.

To confirm that signature verification is active, resend the same body and
timestamp with an invalid signature:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Slack-Request-Timestamp: $SLACK_TIMESTAMP" \
  -H "X-Slack-Signature: v0=invalid" \
  --data-binary @slack-message.json
```

This request returns `401 Unauthorized`. Generate a new timestamp and signature
if more than five minutes have passed. If a calculated signature fails, verify
that the body passed to `--data-binary` is byte-for-byte identical to the body
used to calculate the digest.

## Related pages

- [Webhooks](../webhooks.md)
- [Slack webhook triggers](../triggers.md#slack-webhook-triggers)
- [GitHub webhooks](github.md)
- [Custom webhooks](custom.md)
- [Slack alerter](../../../component-guide/alerters/slack.md)
