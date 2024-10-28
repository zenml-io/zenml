---
icon: message-exclamation
description: Sending automated alerts to chat services.
icon: message-exclamation
---

# Alerters

**Alerters** allow you to send messages to chat services (like Slack, Discord, Mattermost, etc.) from within your pipelines. This is useful to immediately get notified when failures happen, for general monitoring/reporting, and also for building human-in-the-loop ML.

## Alerter Flavors

Currently, the [SlackAlerter](slack.md) and [DiscordAlerter](discord.md) are the available alerter integrations. However, it is straightforward to extend ZenML and [build an alerter for other chat services](custom.md).

| Alerter                            | Flavor    | Integration | Notes                                                              |
| ---------------------------------- | --------- | ----------- | ------------------------------------------------------------------ |
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

Afterward, you can import the alerter standard steps provided by the respective integration and directly use them in your pipelines.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
