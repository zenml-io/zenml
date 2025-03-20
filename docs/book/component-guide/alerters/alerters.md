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

ZenML now provides a **unified** step for posting alerts, regardless of which alerter flavor you’ve chosen. Simply import
and use `alerter_post_step`, passing an `AlerterMessage` object that you can fill with details:

```python
from zenml.alerter.steps.alerter_post_step import alerter_post_step
from zenml.alerter.message_models import AlerterMessage
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

### 3. Use `alerter_ask_step` (Optional)

If your chosen alerter flavor supports interactive approvals (like Slack or Discord), you can incorporate a human-in-the-loop
before continuing:

```python
from zenml.alerter.steps.alerter_ask_step import alerter_ask_step

@pipeline
def my_interactive_pipeline():
    # ...
    user_approved = alerter_ask_step(
        AlerterMessage(
            title="Should I proceed?",
            body="Type 'approve' or 'no' in chat..."
        )
    )
    # The pipeline can then branch logic based on user_approved
```

If the underlying alerter doesn’t support interactive approvals (e.g., SMTP Email), a `NotImplementedError`
may be raised or it will always return `False`.

## Specialized Steps: Deprecated

We previously provided specialized steps for Slack, Discord, and Email:
- `slack_alerter_post_step`, `slack_alerter_ask_step`
- `discord_alerter_post_step`, `discord_alerter_ask_step`
- `smtp_email_alerter_post_step`

These steps are **deprecated** and will be removed in a future release. Please migrate to the generic
`alerter_post_step` and `alerter_ask_step` as shown above.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>