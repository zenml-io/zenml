---
description: Configure and test GitHub webhook delivery to ZenML.
---

# GitHub webhooks

The GitHub webhook provider authenticates repository webhook deliveries and
maps supported GitHub payloads to a small catalog of semantic events. Consumers
can use this provider-owned event model instead of depending on GitHub's raw
payload structure. [Webhook triggers](../triggers.md#webhook-triggers) are the
currently documented consumer that exposes this event configuration.

## Create the webhook in ZenML

Create a GitHub webhook in the active project:

```bash
zenml webhook create github-ml-pipelines --type github
```

Copy the generated signing secret when it is printed. Then describe the webhook
and copy its endpoint URL:

```bash
zenml webhook describe github-ml-pipelines
```

Via the SDK:

```python
from zenml.client import Client
from zenml.webhooks.providers import BuiltinWebhookType

client = Client()
result = client.create_webhook(
    name="github-ml-pipelines",
    webhook_type=BuiltinWebhookType.GITHUB,
)

endpoint_url = result.endpoint_url
signing_secret = result.secret.get_secret_value()
```

The generated secret is available only in the create response. See
[Create a webhook](../webhooks.md#create-a-webhook) for secret-management and
rotation options.

## Configure the repository in GitHub

You need repository administrator access to add the webhook.

1. Open the GitHub repository and go to **Settings** > **Webhooks**.
2. Select **Add webhook**.
3. Set **Payload URL** to the endpoint URL returned by ZenML.
4. Set **Content type** to `application/json`.
5. Set **Secret** to the signing secret returned by ZenML.
6. Choose individual events and select **Pull requests**, **Workflow runs**,
   **Pushes**, **Releases**, and **Issues** as needed by your consumers.
7. Leave the webhook active and select **Add webhook**.

GitHub sends an `X-Hub-Signature-256` header containing an HMAC-SHA256
signature over the exact request body. ZenML verifies this signature before it
parses or forwards the delivery.

## Supported events and filters

The provider recognizes five raw GitHub event families and maps qualifying
payloads to ZenML semantic events:

| GitHub repository event | Raw `X-GitHub-Event` | ZenML semantic event | Required payload condition | Available filter fields |
|-------------------------|----------------------|----------------------|----------------------------|-------------------------|
| Pull requests | `pull_request` | `merged_pull_request` | Action is `closed` and the pull request is merged | `repo`, `target_branch`, `source_branch`, `author` |
| Workflow runs | `workflow_run` | `workflow_run_completed` | Action is `completed` | `workflow`, `conclusion`, `actor` |
| Pushes | `push` | `push` | Ref is a branch under `refs/heads/` | `repo`, `branch`, `actor` |
| Releases | `release` | `release_published` | Action is `published` | `repo`, `tag`, `target_branch`, `actor` |
| Issues | `issues` | `issue_opened` | Action is `opened` | `repo`, `author`, `author_association`, `labels`, `assignees`, `milestone` |

`repo` is the full GitHub repository name, such as `acme/ml-pipelines`. Branch
and tag values do not include Git ref prefixes such as `refs/heads/`.

An unsupported, non-empty raw GitHub event family returns `202 Accepted` and is
ignored before ZenML looks up the webhook or reads the body. A missing or empty
`X-GitHub-Event` header returns `400 Bad Request`.

### String filters

Semantic event fields use ZenML string filters (`StringFilterOption`). You can
use:

- a plain string for exact equality, such as `repo: acme/ml-pipelines`;
- `oneof:` with a non-empty JSON list for exact alternatives, such as
  `conclusion: 'oneof:["success","neutral"]'`;
- `startswith:` for branch-, tag-, and ref-like fields, such as
  `branch: startswith:release/`.

Values configured for the same field use OR logic; different populated fields
use AND logic. Omitted fields match any value. If a configured field is absent
from a delivery, it does not match.

For the collection-valued `labels` and `assignees` fields, a filter matches if
any value on the issue matches any configured value. For example, this target
matches an issue carrying either the `bug` or `priority-high` label:

```yaml
target_events:
  - type: issue_opened
    repo: acme/ml-pipelines
    labels: 'oneof:["bug","priority-high"]'
```

The propagated `issue_opened` event includes the repository, issue number,
title, author, author association, label names, assignee login names, milestone
title, and issue type name when available. It intentionally omits the issue
body. A downstream pipeline can retrieve the complete issue from GitHub using
the repository and issue number.

For example, this target matches pushes to `main` or any `release/` branch in
one repository:

```yaml
target_events:
  - type: push
    repo: acme/ml-pipelines
    branch:
      - main
      - "startswith:release/"
```

Not every operator applies to every field. `oneof:` is supported by the fields
in the table, while `startswith:` is limited to `branch`, `target_branch`,
`source_branch`, and `tag` fields. The issue title, number, and issue type are
available in the propagated event but are not trigger filters.

See [Webhook triggers](../triggers.md#webhook-triggers) for a complete example
that uses this configuration to execute a pipeline snapshot.

## Mock a signed GitHub push

You can test the endpoint without asking GitHub to send a delivery. This example
uses a minimal GitHub-like push payload; the important part is signing and
sending exactly the same bytes.

Set the endpoint and the signing secret captured when you created the webhook:

```bash
export WEBHOOK_URL="<endpoint-url-from-zenml>"
export WEBHOOK_SECRET="<signing-secret>"
```

Write the request body without adding a trailing newline:

```bash
printf '%s' '{"ref":"refs/heads/main","repository":{"full_name":"acme/ml-pipelines"},"sender":{"login":"octocat"}}' > github-push.json
```

Calculate the signature over the file's exact bytes:

```bash
export SIGNATURE="$(python -c 'import hashlib,hmac,os; body=open("github-push.json","rb").read(); print("sha256=" + hmac.new(os.environ["WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest())')"
```

Send those same bytes with the GitHub headers:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: manual-delivery-001" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  --data-binary @github-push.json
```

A valid delivery returns `202 Accepted`. This confirms webhook intake, not that
a consumer matched or a pipeline run started.

To confirm that signature verification is active, send the same body with an
invalid signature:

```bash
curl -i -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: manual-delivery-002" \
  -H "X-Hub-Signature-256: sha256=invalid" \
  --data-binary @github-push.json
```

This request returns `401 Unauthorized`. If a calculated signature fails,
verify that the bytes passed to `--data-binary` are the bytes used to calculate
the digest; even a whitespace or newline change produces a different signature.

## Related pages

- [Webhooks](../webhooks.md)
- [Custom webhooks](custom.md)
- [Webhook triggers](../triggers.md#webhook-triggers)
