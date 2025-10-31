---
description: Sending automated alerts to a Discord channel.
---

# Discord Alerter

The `DiscordAlerter` enables you to send messages to a dedicated Discord channel directly from within your ZenML pipelines.

ZenML provides generic alerter steps that work with any alerter flavor, including Discord:

* `alerter_post_step` takes an `AlerterMessage` object, posts it to a Discord channel using the active alerter, and returns whether the operation was successful.
* `alerter_ask_step` also posts a message to a Discord channel, but waits for user feedback, and only returns `True` if a user explicitly approved the operation.

{% hint style="warning" %}
The specialized Discord steps (`discord_alerter_post_step` and `discord_alerter_ask_step`) are deprecated and will be removed in a future release. Please migrate to the generic `alerter_post_step` and `alerter_ask_step` steps which work with any alerter flavor.
{% endhint %}

Interacting with Discord from within your pipelines can be very useful in practice:

* The alerter steps allow you to get notified immediately when failures happen (e.g., model performance degradation, data drift, etc.).
* The ask functionality allows you to integrate a human-in-the-loop into your pipelines before executing critical steps, such as deploying new models.

## How to use it

### Requirements

Before you can use the `DiscordAlerter`, you first need to install ZenML's `discord` integration:

```shell
zenml integration install discord -y
```

{% hint style="info" %}
See the [Integrations](https://docs.zenml.io/component-guide) page for more details on ZenML integrations and how to install and use them.
{% endhint %}

### Setting Up a Discord Bot

In order to use the `DiscordAlerter`, you first need to have a Discord workspace set up with a channel that you want your pipelines to post to. This is the `<DISCORD_CHANNEL_ID>` you will need when registering the discord alerter component.

Then, you need to [create a Discord App with a bot in your server](https://discordpy.readthedocs.io/en/latest/discord.html) .

{% hint style="info" %}
Note in the bot token copy step, if you don't find the copy button then click on reset token to reset the bot and you will get a new token which you can use. Also, make sure you give necessary permissions to the bot required for sending and receiving messages.
{% endhint %}

### Registering a Discord Alerter in ZenML

Next, you need to register a `discord` alerter in ZenML and link it to the bot you just created. You can do this with the following command:

```shell
zenml alerter register discord_alerter \
    --flavor=discord \
    --discord_token=<DISCORD_TOKEN> \
    --default_discord_channel_id=<DISCORD_CHANNEL_ID>
```

{% hint style="info" %}
**Using Secrets for Token Management**: Instead of passing your Discord token directly, it's recommended to store it as a ZenML secret and reference it in your alerter configuration. This approach keeps sensitive information secure:

```shell
# Create a secret for your Discord token
zenml secret create discord_secret --discord_token=<DISCORD_TOKEN>

# Register the alerter referencing the secret
zenml alerter register discord_alerter \
    --flavor=discord \
    --discord_token={{discord_secret.discord_token}} \
    --default_discord_channel_id=<DISCORD_CHANNEL_ID>
```

Learn more about [referencing secrets in stack component attributes and settings](https://docs.zenml.io/concepts/secrets#reference-secrets-in-stack-component-attributes-and-settings).
{% endhint %}

After you have registered the `discord_alerter`, you can add it to your stack like this:

```shell
zenml stack register ... -al discord_alerter
```

Here is where you can find the required parameters:

#### DISCORD\_CHANNEL\_ID

Open the discord server, then right-click on the text channel and click on the 'Copy Channel ID' option.

{% hint style="info" %}
If you don't see any 'Copy Channel ID' option for your channel, go to "User Settings" > "Advanced" and make sure "Developer Mode" is active.
{% endhint %}

#### DISCORD\_TOKEN

This is the Discord token of your bot. You can find the instructions on how to set up a bot, invite it to your channel, and find its token [here](https://discordpy.readthedocs.io/en/latest/discord.html).

{% hint style="warning" %}
When inviting the bot to your channel, make sure it has at least the following permissions:

* Read Messages/View Channels
* Send Messages
* Send Messages in Threads
{% endhint %}

### How to Use the Discord Alerter

#### Using the Generic Alerter Steps

After you have a `DiscordAlerter` configured in your stack, you can use the generic alerter steps that work with any alerter flavor:

```python
from zenml.alerter.steps.alerter_post_step import alerter_post_step
from zenml.alerter.steps.alerter_ask_step import alerter_ask_step
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml import step, pipeline


@step
def my_formatter_step(artifact_to_be_communicated) -> AlerterMessage:
    # Create a structured message with title, body, and metadata
    return AlerterMessage(
        title="Pipeline Update",
        body=f"Here is my artifact {artifact_to_be_communicated}!",
        metadata={"artifact_type": type(artifact_to_be_communicated).__name__}
    )


@pipeline
def my_pipeline(...):
    ...
    artifact_to_be_communicated = ...
    message = my_formatter_step(artifact_to_be_communicated)
    
    # Post the message
    alerter_post_step(message)
    
    # Or ask for user approval
    approval_message = AlerterMessage(
        title="Approval Required",
        body="Should we proceed with the deployment?",
        metadata={"critical": True}
    )
    approved = alerter_ask_step(approval_message)
    ... # Potentially have different behavior in subsequent steps if `approved`

if __name__ == "__main__":
    my_pipeline()
```

#### Using AlerterMessage Directly

You can also use the `AlerterMessage` model directly with the Discord alerter's `post()` and `ask()` methods:

```python
from zenml.client import Client
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml import step

@step
def alert_step():
    # Get the active alerter from the stack
    alerter = Client().active_stack.alerter
    
    # Create a structured message
    msg = AlerterMessage(
        title="Processing Complete",
        body="All data processing steps have finished successfully.",
        metadata={"execution_time": "10m 23s", "records_processed": 5432}
    )
    
    # Send the alert
    alerter.post(message=msg)

@step
def approval_step() -> bool:
    # Get the active alerter from the stack
    alerter = Client().active_stack.alerter
    
    # Create a question message
    question = AlerterMessage(
        title="Deployment Approval",
        body="The model is ready for deployment. Should we proceed?",
        metadata={"model_accuracy": 0.95, "requires_approval": True}
    )
    
    # Ask for approval
    return alerter.ask(question=question)
```

#### Using the Deprecated Discord-Specific Steps

For backward compatibility, you can still use the Discord-specific steps, but they will show deprecation warnings:

```python
from zenml.integrations.discord.steps.discord_alerter_ask_step import discord_alerter_ask_step
from zenml.integrations.discord.steps.discord_alerter_post_step import discord_alerter_post_step
from zenml import step, pipeline


@step
def my_formatter_step(artifact_to_be_communicated) -> str:
    return f"Here is my artifact {artifact_to_be_communicated}!"


@step
def process_approval_response(artifact, approved: bool) -> None:
    if approved:
        # Proceed with the operation
        print(f"User approved! Processing {artifact}")
        # Your logic here
    else:
        print("User disapproved. Skipping operation.")


@pipeline
def my_pipeline(...):
    ...
    artifact_to_be_communicated = ...
    message = my_formatter_step(artifact_to_be_communicated)
    
    # Post message (deprecated approach)
    discord_alerter_post_step(message)
    
    # Ask for approval (deprecated approach)
    approved = discord_alerter_ask_step("Should we proceed with the deployment?")
    process_approval_response(artifact_to_be_communicated, approved)

if __name__ == "__main__":
    my_pipeline()
```

## Using Custom Approval Keywords

You can customize which words trigger approval or disapproval by using `DiscordAlerterParameters`:

```python
from zenml.integrations.discord.steps.discord_alerter_ask_step import discord_alerter_ask_step
from zenml.integrations.discord.alerters.discord_alerter import DiscordAlerterParameters

# Custom approval/disapproval keywords
params = DiscordAlerterParameters(
    approve_msg_options=["deploy", "ship it", "✅"],
    disapprove_msg_options=["stop", "cancel", "❌"]
)

approved = discord_alerter_ask_step(
    "Deploy model to production?", 
    params=params
)
```

## Using Discord Alerter with Hooks

You can use the Discord alerter with pipeline hooks to automatically send notifications when your pipeline succeeds or fails:

```python
from zenml import pipeline, step
from zenml.hooks import alerter_success_hook, alerter_failure_hook

@step
def model_training_step() -> float:
    # Your model training logic here
    accuracy = 0.92
    return accuracy

# Apply hooks at the pipeline level
@pipeline(
    on_success=alerter_success_hook,
    on_failure=alerter_failure_hook
)
def ml_pipeline():
    model_training_step()

# Or apply hooks at the step level  
@step(
    on_success=alerter_success_hook,
    on_failure=alerter_failure_hook
)
def critical_deployment_step():
    # Deployment logic here
    pass
```

The alerter hooks use the new `AlerterMessage` format internally, which provides structured alerts with:
- **Title**: "Pipeline Success Notification" or "Pipeline Failure Alert"
- **Body**: Detailed information about the pipeline, step, and context
- **Metadata**: Additional context like pipeline name, run ID, and stack name

For failure hooks, the full exception traceback is included in the alert, formatted appropriately for Discord.

### Default Response Keywords

By default, the Discord alerter recognizes these keywords:

**Approval:** `approve`, `LGTM`, `ok`, `yes`  
**Disapproval:** `decline`, `disapprove`, `no`, `reject`

**Important Notes:**
- The ask step returns a boolean (`True` for approval, `False` for disapproval/timeout)
- **Keywords are case-sensitive** - you must respond with exact case (e.g., `LGTM` not `lgtm`)
- If no valid response is received, the step returns `False`

{% hint style="warning" %}
**Discord Case Sensitivity**: The Discord alerter implementation requires exact case matching for approval keywords. Make sure to respond with the exact case specified (e.g., `LGTM`, not `lgtm`).
{% endhint %}

For more information and a full list of configurable attributes of the Discord alerter, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-discord.html#zenml.integrations.discord) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>