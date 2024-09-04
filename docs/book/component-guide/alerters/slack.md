---
description: Sending automated alerts to a Slack channel.
---

# Slack Alerter

The `SlackAlerter` enables you to send messages to a dedicated Slack channel directly from within your ZenML pipelines.

The `slack` integration contains the following two standard steps:

* [slack\_alerter\_post\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-slack/#zenml.integrations.slack.steps.slack\_alerter\_post\_step.slack\_alerter\_post\_step) takes a string message or a custom [Slack block](https://api.slack.com/block-kit/building), posts it to a Slack channel, and returns whether the operation was successful.
* [slack\_alerter\_ask\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-slack/#zenml.integrations.slack.steps.slack\_alerter\_ask\_step.slack\_alerter\_ask\_step) also posts a message or a custom [Slack block](https://api.slack.com/block-kit/building) to a Slack channel, but waits for user feedback, and only returns `True` if a user explicitly approved the operation from within Slack (e.g., by sending "approve" / "reject" to the bot in response).

Interacting with Slack from within your pipelines can be very useful in practice:

* The `slack_alerter_post_step` allows you to get notified immediately when failures happen (e.g., model performance degradation, data drift, ...),
* The `slack_alerter_ask_step` allows you to integrate a human-in-the-loop into your pipelines before executing critical steps, such as deploying new models.

## How to use it

### Requirements

Before you can use the `SlackAlerter`, you first need to install ZenML's `slack` integration:

```shell
zenml integration install slack -y
```

{% hint style="info" %}
See the [Integrations](../README.md) page for more details on ZenML integrations and how to install and use them.
{% endhint %}

### Setting Up a Slack Bot

In order to use the `SlackAlerter`, you first need to have a Slack workspace set up with a channel that you want your pipelines to post to.

Then, you need to [create a Slack App](https://api.slack.com/apps?new\_app=1) with a bot in your workspace.

{% hint style="info" %}
Make sure to give your Slack bot the following permissions in the `OAuth & Permissions` tab under `Scopes`:

* `chat:write`,
* `chat:write.public`
* `channels:read`
* `groups:read`
* `im:read`
* `mpim:read`

![Slack OAuth Permissions](../../.gitbook/assets/slack-alerter-oauth-permissions.png)

{% endhint %}

### Registering a Slack Alerter in ZenML

Next, you need to register a `slack` alerter in ZenML and link it to the bot you just created. You can do this with the following commands:

```shell
zenml secret create slack_token --oauth_token=<SLACK_TOKEN>
zenml alerter register slack_alerter \
    --flavor=slack \
    --slack_token='{{ slack_token:oauth_token }}' \
    --default_slack_channel_id=<SLACK_CHANNEL_ID>
```

Here is where you can find the required parameters:

* `<SLACK_CHANNEL_ID>`: Open your desired Slack channel in a browser, and copy out the last part of the URL starting with `C....`.
* `<SLACK_TOKEN>`: This is the Slack token of your bot. You can find it in the Slack app settings under `OAuth & Permissions`. **IMPORTANT**: Please make sure that the token is the `Bot User OAuth Token` not the `User OAuth Token`.

![Slack Token Image](../../.gitbook/assets/slack-alerter-token.jpg)

After you have registered the `slack_alerter`, you can add it to your stack like this:

```shell
zenml stack register ... -al slack_alerter
```

### How to Use the Slack Alerter

After you have a `SlackAlerter` configured in your stack, you can directly import the [slack\_alerter\_post\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-slack/#zenml.integrations.slack.steps.slack\_alerter\_post\_step.slack\_alerter\_post\_step) and [slack\_alerter\_ask\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-slack/#zenml.integrations.slack.steps.slack\_alerter\_ask\_step.slack\_alerter\_ask\_step) steps and use them in your pipelines.

Since these steps expect a string message as input (which needs to be the output of another step), you typically also need to define a dedicated formatter step that takes whatever data you want to communicate and generates the string message that the alerter should post.

As an example, adding `slack_alerter_ask_step()` to your pipeline could look like this:

```python
from zenml.integrations.slack.steps.slack_alerter_ask_step import slack_alerter_ask_step
from zenml import step, pipeline


@step
def my_formatter_step(artifact_to_be_communicated) -> str:
    return f"Here is my artifact {artifact_to_be_communicated}!"


@pipeline
def my_pipeline(...):
    ...
    artifact_to_be_communicated = ...
    message = my_formatter_step(artifact_to_be_communicated)
    approved = slack_alerter_ask_step(message)
    ... # Potentially have different behavior in subsequent steps if `approved`

if __name__ == "__main__":
    my_pipeline()
```

An example of adding a custom Slack block as part of any alerter logic for your pipeline could look like this:

```python
from typing import List, Dict
from zenml.integrations.slack.steps.slack_alerter_ask_step import slack_alerter_post_step
from zenml.integrations.slack.alerters.slack_alerter import SlackAlerterParameters
from zenml import step, pipeline


@step
def my_custom_block_step(block_message) -> List[Dict]:
    my_custom_block = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": f":tada: {block_message}",
				"emoji": true
			}
		}
	]
    return SlackAlerterParameters(blocks = my_custom_block)


@pipeline
def my_pipeline(...):
    ...
    message_blocks = my_custom_block_step("my custom block!")
    post_message = slack_alerter_post_step(params = message_blocks)
    return post_message

if __name__ == "__main__":
    my_pipeline()

```

For more information and a full list of configurable attributes of the Slack alerter, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-slack/#zenml.integrations.slack.alerters.slack\_alerter.SlackAlerter) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
