---
description: Sending automated alerts to chat services.
icon: message-exclamation
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Alerters

**Alerters** allow you to send messages to chat services (like Slack, Discord, Mattermost, etc.) from within your
pipelines. This is useful to immediately get notified when failures happen, for general monitoring/reporting, and also
for building human-in-the-loop ML.

## Alerter Flavors

Currently, the [SlackAlerter](slack.md) and [DiscordAlerter](discord.md) are the available alerter integrations. However, it is straightforward to
extend ZenML and [build an alerter for other chat services](custom.md).

| Alerter                            | Flavor    | Integration | Notes                                                              |
|------------------------------------|-----------|-------------|--------------------------------------------------------------------|
| [Slack](slack.md)                  | `slack`   | `slack`     | Interacts with a Slack channel                                     |
| [Discord](discord.md)              | `discord` | `discord`   | Interacts with a Discord channel                                   |
| [Custom Implementation](custom.md) | _custom_  |             | Extend the alerter abstraction and provide your own implementation |

{% hint style="info" %}
If you would like to see the available flavors of alerters in your terminal, you can use the following command:

```shell
zenml alerter flavor list
```

{% endhint %}

## How to use Alerters with ZenML

Each alerter integration comes with specific standard steps that you can use out of the box.

However, you first need to register an alerter component in your terminal:

```shell
zenml alerter register <ALERTER_NAME> ...
```

Then you can add it to your stack using

```shell
zenml stack register ... -al <ALERTER_NAME>
```

Afterward, you can import the alerter standard steps provided by the respective integration and directly use them in
your pipelines.

## Using the Ask Step for Human-in-the-Loop Workflows

All alerters provide an `ask()` method and corresponding ask steps that enable human-in-the-loop workflows. These are essential for:

- Getting approval before deploying models to production
- Confirming critical pipeline decisions  
- Manual intervention points in automated workflows

### How Ask Steps Work

Ask steps (like `discord_alerter_ask_step` and `slack_alerter_ask_step`):

1. **Post a message** to your chat service with your question
2. **Wait for user response** containing specific approval or disapproval keywords
3. **Return a boolean** - `True` if approved, `False` if disapproved or timeout

```python
from zenml import step, pipeline
from zenml.integrations.slack.steps.slack_alerter_ask_step import slack_alerter_ask_step

@step
def train_model():
    # Training logic here - this is a placeholder function
    return "trained_model_object"

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
    approved = slack_alerter_ask_step("Deploy model to production?")
    deploy_model(trained_model, approved)
```

### Default Response Keywords

By default, alerters recognize these response options:

**Approval:** `approve`, `LGTM`, `ok`, `yes`  
**Disapproval:** `decline`, `disapprove`, `no`, `reject`

### Customizing Response Keywords

You can customize the approval and disapproval keywords using alerter parameters:

```python
from zenml.integrations.slack.steps.slack_alerter_ask_step import slack_alerter_ask_step
from zenml.integrations.slack.alerters.slack_alerter import SlackAlerterParameters

# Use custom approval/disapproval keywords
params = SlackAlerterParameters(
    approve_msg_options=["deploy", "ship it", "✅"],
    disapprove_msg_options=["stop", "cancel", "❌"]
)

approved = slack_alerter_ask_step(
    "Deploy model to production?", 
    params=params
)
```

### Important Notes

- **Return Type**: Ask steps return a boolean value - ensure your pipeline logic handles this correctly
- **Keywords**: Response keywords are case-sensitive (except Slack, which converts to lowercase)
- **Timeout**: If no valid response is received within the timeout period, the step returns `False`
- **Permissions**: Ensure your bot has permissions to read messages in the target channel

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
