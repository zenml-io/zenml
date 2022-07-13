---
description: Sending alerts through specified channels.
---

Alerters allow you to send messages to chat services (like Slack, Discord, 
Mattermost, etc.) from within your pipeline.
This is useful for immediately getting notified when failures happen,
for general monitoring/reporting, and also for building human-in-the-loop ML.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](../advanced-guide/stacks-components-flavors.md).  
{% endhint %}

## Base Abstraction

The base abstraction for alerters is very basic, as it only defines two
abstract methods that subclasses should implement:
- `post()` takes a string, posts it to the desired chat service, and returns 
`True` if the operation succeeded, else `False`.
- `ask()` does the same as `post()`, but after sending the message, it waits
until someone approves or rejects the operation from within the chat service
(e.g., by sending "approve" / "reject" to the bot as response).
`ask()` then only returns `True` if the operation succeeded and was approved,
else `False`.

Then base abstraction looks something like this:

```python
class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    def post(
        self, message: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service."""
        return True

    def ask(
        self, question: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service and wait for approval."""
        return True
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation.
To see the full docstrings and imports, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/alerter/base_alerter.py).
{% endhint %}

## List of available alerters

Currently, the only available alerter integration is Slack.
The Slack alerter can be used to post/ask in a specified Slack channel via a 
dedicated bot account of a Slack app linked to the channel.

|                | Flavor | Integration |
|----------------|--------|-------------|
| [SlackAlerter](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.alerters.slack_alerter.SlackAlerter)   | slack  | slack       |

If you would like to see the available flavors for alerters, you can use the 
command:

```shell
zenml alerter flavor list
```

## Build your own custom alerter

Creating your own custom alerter can be done in three steps:

1. Create a class that inherits from the `BaseAlerter`.
2. Define the `FLAVOR` class variable in your class (e.g., `FLAVOR="discord"`)
3. Implement the `post()` and `ask()` methods for your alerter.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml alerter flavor register <THE-SOURCE-PATH-OF-YOUR-ALERTER>
```