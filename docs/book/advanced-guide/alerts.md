---
description: Send automated alerts to chat services.
---

# :speech_balloon: Send Automated Chat Alerts

Many developer teams use real-time chat services like Slack for their
day-to-day communication. Sometimes it can also be desired to have automated
notifications be sent to those chat services from within ML pipelines,
e.g., to quickly and conveniently get notified about the state of
each pipeline, or even to build human-in-the-loop ML systems.

## Overview

The `alerter` component in ZenML allows teams to easily interact with their
pipelines via a chat service.

To use alerters in a ML pipeline, ZenML provides two standard steps
in `zenml.alerter.alerter_step`:
- `alerter_post_step()` takes a string, posts it to 
the desired chat service, and returns `True` if the operation succeeded, 
else `False`.
- `alerter_ask_step()`: does the same as 
`alerter_post_step()`, but after sending the message, it waits
until someone approves or rejects the operation from within the chat service
(e.g., by sending "approve" / "reject" to the bot as response).
`alerter_ask_step()` then only returns `True` if the operation succeeded and 
was approved, else `False`.

To use those steps with your preferred chat service, you only need to register
a corresponding `alerter` component in your ZenML stack.
Right now, the
[SlackAlerter](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.alerters.slack_alerter.SlackAlerter)
is the only alerter you can use out-of-the-box, but it is straightforward to 
extend ZenML and build an alerter for other chat services, as shown 
[here](https://docs.zenml.io/extending-zenml/alerter).

## Send alerts in your pipelines

To send alerts in your pipelines, you first need to register an alerter
component using `zenml alerter register <MY_ALERTER>` and then add it to your 
stack with `zenml stack register ... -al <MY_ALERTER>`.

Afterward, you can simply import the standard alerter steps and use them in
your pipeline.

Since these steps expect a string message as input (which needs to be the 
output of another step), you typically also need to define a dedicated 
formatter step that takes whatever data you want to communicate and generates
the string message that the alerter should post.

As an example, adding `alerter_ask_step()` into your pipeline could look like
this:

```python
from zenml.alerter.alerter_step import alerter_ask_step
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
    alerter=alerter_ask_step(),
).run()
```

For complete code examples of both alerter steps, see the `slack_alert` example
[here](https://github.com/zenml-io/zenml/tree/main/examples/slack_alert),
where we first send the test accuracy of a model to Slack and then wait with
model deployment until a user approves it in Slack.
