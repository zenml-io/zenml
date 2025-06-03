---
description: Sending automated alerts to chat services and email.
icon: message-exclamation
---

# Alerters

**Alerters** allow you to send messages to chat services (like Slack, Discord, etc.) or via email from within your
pipelines. This is useful to immediately get notified about failures, for general monitoring/reporting, or
for building human-in-the-loop ML workflows.

## Alerter Flavors

Currently, the [SlackAlerter](slack.md), [DiscordAlerter](discord.md), and [SMTP Email Alerter](smtp_email.md) are the available alerter integrations. However, it is straightforward to extend ZenML and [build an alerter for other services](custom.md).

| Alerter                            | Flavor        | Integration   | Notes                                                              |
|------------------------------------|---------------|---------------|--------------------------------------------------------------------|
| [Slack](slack.md)                  | `slack`       | `slack`       | Interacts with a Slack channel                                     |
| [Discord](discord.md)              | `discord`     | `discord`     | Interacts with a Discord channel                                   |
| [SMTP Email](smtp_email.md)        | `smtp_email`  | `smtp_email`  | Sends email notifications via SMTP                                 |
| [Custom Implementation](custom.md) | _custom_      |               | Extend the alerter abstraction and provide your own implementation |

{% hint style="info" %}
If you would like to see the available flavors of alerters in your terminal, you can use the following command:

```shell
zenml alerter flavor list
```
{% endhint %}

## How to Use Alerters with ZenML

### 1. Register an Alerter

First, you register the alerter flavor of your choice. For example, for Slack:

```shell
zenml alerter register my_slack_alerter \
    --flavor=slack \
    --slack_token=<YOUR_SLACK_BOT_TOKEN> \
    --slack_channel_id=<YOUR_SLACK_CHANNEL_ID>
```

Then attach it to your stack:

```shell
zenml stack register my_stack -al my_slack_alerter ...
```

### 2. Use `alerter_post_step` (Recommended)

ZenML now provides a **unified** step for posting alerts, regardless of which alerter flavor you've chosen. Simply import
and use `alerter_post_step`, passing an `AlerterMessage` object that you can fill with details:

```python
from zenml.alerter.steps.alerter_post_step import alerter_post_step
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml import pipeline

@pipeline
def my_pipeline():
    # Construct a message with an optional title, body, and extra metadata
    msg = AlerterMessage(
        title="Hello from my pipeline!",
        body="All checks passed successfully.",
        metadata={"accuracy": 0.95, "f1_score": 0.92}
    )
    result = alerter_post_step(msg)
    # result is True if successfully posted, else False
```

When you run this pipeline, ZenML will automatically detect which alerter is configured in your active stack, then post
to Slack, Discord, or send an email, etc. Each flavor interprets the message in its own format (Slack blocks, email HTML, etc.).

### 3. Use `alerter_ask_step` for Human-in-the-Loop Workflows

All alerters provide an `ask()` method and corresponding ask steps that enable human-in-the-loop workflows. These are essential for:

- Getting approval before deploying models to production
- Confirming critical pipeline decisions  
- Manual intervention points in automated workflows

#### How Ask Steps Work

The generic `alerter_ask_step` (and flavor-specific ask steps):

1. **Post a message** to your chat service with your question
2. **Wait for user response** containing specific approval or disapproval keywords
3. **Return a boolean** - `True` if approved, `False` if disapproved or timeout

```python
from zenml.alerter.steps.alerter_ask_step import alerter_ask_step
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml import step, pipeline

@step
def deploy_model(model, approved: bool) -> None:
    if approved:
        # Deploy the model to production
        print("Deploying model to production...")
        # deployment logic here
    else:
        print("Deployment cancelled by user")

@pipeline
def deployment_pipeline():
    trained_model = train_model()
    # Ask for human approval before deployment
    approval_msg = AlerterMessage(
        title="Deployment Approval",
        body="Deploy model to production?"
    )
    approved = alerter_ask_step(approval_msg)
    deploy_model(trained_model, approved)
```

If the underlying alerter doesn't support interactive approvals (e.g., SMTP Email), a `NotImplementedError`
may be raised or it will always return `False`.

#### Default Response Keywords

By default, alerters recognize these response options:

**Approval:** `approve`, `LGTM`, `ok`, `yes`  
**Disapproval:** `decline`, `disapprove`, `no`, `reject`

#### Customizing Response Keywords

You can customize the approval and disapproval keywords using alerter parameters:

```python
from zenml.alerter.steps.alerter_ask_step import alerter_ask_step
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml.integrations.slack.alerters.slack_alerter import SlackAlerterParameters

# Use custom approval/disapproval keywords
params = SlackAlerterParameters(
    approve_msg_options=["deploy", "ship it", "✅"],
    disapprove_msg_options=["stop", "cancel", "❌"]
)

approval_msg = AlerterMessage(
    title="Deployment Approval",
    body="Deploy model to production?"
)

approved = alerter_ask_step(approval_msg, params=params)
```

#### Important Notes

- **Return Type**: Ask steps return a boolean value - ensure your pipeline logic handles this correctly
- **Keywords**: Response keywords are case-sensitive (except Slack, which converts to lowercase)
- **Timeout**: If no valid response is received within the timeout period, the step returns `False`
- **Permissions**: Ensure your bot has permissions to read messages in the target channel

## Specialized Steps: Deprecated

We previously provided specialized steps for Slack, Discord, and Email:
- `slack_alerter_post_step`, `slack_alerter_ask_step`
- `discord_alerter_post_step`, `discord_alerter_ask_step`
- `smtp_email_alerter_post_step`

These steps are **deprecated** and will be removed in a future release. Please migrate to the generic
`alerter_post_step` and `alerter_ask_step` as shown above.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>