---
description: How to send automated alerts to a Slack channel
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Slack Alerter

The `SlackAlerter` enables you to send messages to a dedicated Slack
channel directly from within your pipelines.

The `slack` integration also contains the following two standard steps:
- [slack_alerter_post_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_post_step.slack_alerter_post_step) 
takes a string, posts it to Slack, and returns `True` if the operation 
succeeded, else `False`.
- [slack_alerter_ask_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_ask_step.slack_alerter_ask_step) 
does the same as `slack_alerter_post_step`, but after sending the message, it 
waits until someone approves or rejects the operation from within Slack
(e.g., by sending "approve" / "reject" to the bot in response).
`slack_alerter_ask_step` then only returns `True` if the operation succeeded
and was approved, else `False`.

Interacting with Slack from within your pipelines can be very useful in 
practice:
- The `slack_alerter_post_step` allows you to get notified immediately when 
failures happen (e.g., model performance degradation, data drift, ...),
- The `slack_alerter_ask_step` allows you to integrate a human-in-the-loop into
your pipelines before executing critical steps, such as deploying new models.

## How to use it

### Requirements

Before you can use the `SlackAlerter`, you first need to install ZenML's 
`slack` integration:

```shell
zenml integration install slack -y
```

{% hint style="info" %}
See the [Integrations](../../mlops-stacks/integrations.md) page for more
details on ZenML integrations and how to install and use them.
{% endhint %}

### Setting Up a Slack Bot

In order to use the `SlackAlerter`, you first need to have a Slack workspace set up
with a channel that you want your pipelines to post to.

Then, you need to [create a Slack App](https://api.slack.com/apps?new_app=1)
with a bot in your workspace.

{% hint style="info" %}
Make sure to give your Slack bot `chat:write` and `chat:write.public` 
permissions in the `OAuth & Permissions` tab under `Scopes`.
{% endhint %}

### Registering a Slack Alerter in ZenML

Next, you need to register a `slack` alerter in ZenML and link it to the bot
you just created. You can do this with the following command:

```shell
zenml alerter register slack_alerter \
    --flavor=slack \
    --slack_token=<SLACK_TOKEN> \
    --default_slack_channel_id=<SLACK_CHANNEL_ID>
```

Here is where you can find the required parameters:
- `<SLACK_CHANNEL_ID>`: Open your desired Slack channel in a browser, and copy
out the last part of the URL starting with `C....`.
- `<SLACK_TOKEN>`: This is the Slack token of your bot. You can find it in the
Slack app settings under `OAuth & Permissions`.

After you have registered the `slack_alerter`, you can add it to your stack
like this:

```shell
zenml stack register ... -al slack_alerter
```

### How to Use the Slack Alerter

After you have a `SlackAlerter` configured in your stack, you can directly import the 
[slack_alerter_post_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_post_step.slack_alerter_post_step) and
[slack_alerter_ask_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_ask_step.slack_alerter_ask_step)
steps and use them in your pipelines.

Since these steps expect a string message as input (which needs to be the 
output of another step), you typically also need to define a dedicated 
formatter step that takes whatever data you want to communicate and generates
the string message that the alerter should post.

As an example, adding `slack_alerter_ask_step()` into your pipeline could look
like this:

```python
from zenml.integrations.slack.steps.slack_alerter_ask_step import slack_alerter_ask_step
from zenml.steps import step
from zenml.pipelines import pipeline


@step
def my_formatter_step(artifact_to_be_communicated) -> str:
    return f"Here is my artifact {artifact_to_be_communicated}!"


@pipeline
def my_pipeline(..., formatter, alerter):
    ...
    artifact_to_be_communicated = ...
    message = formatter(artifact_to_be_communicated)
    approved = alerter(message)
    ... # Potentially have different behavior in subsequent steps if `approved`


my_pipeline(
    ...
    formatter=my_formatter_step(),
    alerter=slack_alerter_ask_step(),
).run()
```

For complete code examples of both Slack alerter steps, see the 
[slack alerter example](https://github.com/zenml-io/zenml/tree/main/examples/slack_alert),
where we first send the test accuracy of a model to Slack and then wait with
model deployment until a user approves it in Slack.


For more information and a full list of configurable attributes of the Slack alerter, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.alerters.slack_alerter.SlackAlerter).