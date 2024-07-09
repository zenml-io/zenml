---
description: Sending automated alerts to a Discord channel.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Discord Alerter

The `DiscordAlerter` enables you to send messages to a dedicated Discord channel 
directly from within your ZenML pipelines.

The `discord` integration contains the following two standard steps:

* [discord\_alerter\_post\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-discord/#zenml.integrations.discord.steps.discord\_alerter\_post\_step.discord\_alerter\_post\_step)
  takes a string message, posts it to a Discord channel, and returns whether the 
  operation was successful.
* [discord\_alerter\_ask\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-discord/#zenml.integrations.discord.steps.discord\_alerter\_ask\_step.discord\_alerter\_ask\_step)
  also posts a message to a Discord channel, but waits for user feedback, and 
  only returns `True` if a user explicitly approved the operation from within 
  Discord (e.g., by sending "approve" / "reject" to the bot in response).

Interacting with Discord from within your pipelines can be very useful in practice:

* The `discord_alerter_post_step` allows you to get notified immediately when failures happen (e.g., model performance
  degradation, data drift, ...),
* The `discord_alerter_ask_step` allows you to integrate a human-in-the-loop into your pipelines before executing critical
  steps, such as deploying new models.

## How to use it

### Requirements

Before you can use the `DiscordAlerter`, you first need to install ZenML's `discord` integration:

```shell
zenml integration install discord -y
```

{% hint style="info" %}
See the [Integrations](../README.md) page for more details on ZenML integrations and how to install and
use them.
{% endhint %}

### Setting Up a Discord Bot

In order to use the `DiscordAlerter`, you first need to have a Discord workspace set up with a channel that you want your
pipelines to post to. This is the `<DISCORD_CHANNEL_ID>` you will need when registering the discord alerter component.

Then, you need to [create a Discord App with a bot in your server](https://discordpy.readthedocs.io/en/latest/discord.html)
.

{% hint style="info" %}
Note in the bot token copy step, if you don't find the copy button then click on reset token to reset the bot 
and you will get a new token which you can use. Also, make sure you give necessary permissions to the bot 
required for sending and receiving messages.
{% endhint %}

### Registering a Discord Alerter in ZenML

Next, you need to register a `discord` alerter in ZenML and link it to the bot you just created. You can do this with the
following command:

```shell
zenml alerter register discord_alerter \
    --flavor=discord \
    --discord_token=<DISCORD_TOKEN> \
    --default_discord_channel_id=<DISCORD_CHANNEL_ID>
```

After you have registered the `discord_alerter`, you can add it to your stack like this:

```shell
zenml stack register ... -al discord_alerter
```

Here is where you can find the required parameters:

#### DISCORD_CHANNEL_ID

Open the discord server, then right-click on the text channel and click on the 
'Copy Channel ID' option.

{% hint style="info" %}
If you don't see any 'Copy Channel ID' option for your channel, go to "User Settings" > "Advanced" and make sure "Developer Mode" is active.
{% endhint %}

#### DISCORD_TOKEN

This is the Discord token of your bot. You can find the instructions on how to set up a bot, invite it to your channel, and find its token
[here](https://discordpy.readthedocs.io/en/latest/discord.html).

{% hint style="warning" %}
When inviting the bot to your channel, make sure it has at least the following
permissions: 
* Read Messages/View Channels
* Send Messages
* Send Messages in Threads
{% endhint %}

### How to Use the Discord Alerter

After you have a `DiscordAlerter` configured in your stack, you can directly import
the [discord\_alerter\_post\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-discord/#zenml.integrations.discord.steps.discord\_alerter\_post\_step.discord\_alerter\_post\_step)
and [discord\_alerter\_ask\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-discord/#zenml.integrations.discord.steps.discord\_alerter\_ask\_step.discord\_alerter\_ask\_step)
steps and use them in your pipelines.

Since these steps expect a string message as input (which needs to be the output of another step), you typically also
need to define a dedicated formatter step that takes whatever data you want to communicate and generates the string
message that the alerter should post.

As an example, adding `discord_alerter_ask_step()` to your pipeline could look like this:

```python
from zenml.integrations.discord.steps.discord_alerter_ask_step import discord_alerter_ask_step
from zenml import step, pipeline


@step
def my_formatter_step(artifact_to_be_communicated) -> str:
    return f"Here is my artifact {artifact_to_be_communicated}!"


@pipeline
def my_pipeline(...):
    ...
    artifact_to_be_communicated = ...
    message = my_formatter_step(artifact_to_be_communicated)
    approved = discord_alerter_ask_step(message)
    ... # Potentially have different behavior in subsequent steps if `approved`

if __name__ == "__main__":
    my_pipeline()
```

For more information and a full list of configurable attributes of the Discord alerter, check out
the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-discord/#zenml.integrations.discord.alerters.discord\_alerter.DiscordAlerter)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
