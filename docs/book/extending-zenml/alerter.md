---
description: Sending alerts through specified channels.
---

Alerters allow you to send alerts from within your pipeline. This is especially 
useful to immediately get notified when failures happen, and also for 
general monitoring/reporting.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the alerters, which 
will be available soon. As a result, their extension is not possible at the 
moment. If you would like to use an alerter in your stack, please check the list 
of already available alerters down below.
{% endhint %}

## List of available alerters

When it comes to alerters, ZenML comes with an integration into Slack, which 
can be used to post messages to a specified channel.

|                | Flavor | Integration |
|----------------|--------|-------------|
| SlackAlerter   | slack  | slack       |

If you would like to see the available flavors for alerters, you can 
use the command:

```shell
zenml alerter flavor list
```