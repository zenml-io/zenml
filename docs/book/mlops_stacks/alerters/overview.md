---
description: Send automated alerts to chat services.
---

- `What is it, what does it do`
- `Why would you want to use it`
- `When should you start adding this to your stack`
- `Overview of flavors, tradeoffs, when to use which flavor (table)`


# :speech_balloon: Send Automated Chat Alerts

Many developer teams use real-time chat services like Slack for their
day-to-day communication. Members of those teams might also want to have automated
notifications be sent to those chat services from within ML pipelines,
e.g., to quickly and conveniently get notified about the state of
each pipeline, or even to build human-in-the-loop ML systems.

## Overview

The `alerter` component in ZenML allows teams to interact with their
pipelines via a chat service. 

Each alerter integration comes with specific standard steps that you can
use out-of-the-box. 
As an example, the `slack` integration contains the following two steps:
- [slack_alerter_post_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_post_step.slack_alerter_post_step) 
takes a string, posts it to Slack, and returns `True` if the operation 
succeeded, else `False`.
- [slack_alerter_ask_step](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_ask_step.slack_alerter_ask_step) 
does the same as `slack_alerter_post_step`, but after sending the message, it 
waits until someone approves or rejects the operation from within Slack
(e.g., by sending "approve" / "reject" to the bot in response).
`slack_alerter_ask_step` then only returns `True` if the operation succeeded
and was approved, else `False`.

Currently, the
[SlackAlerter](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.slack.steps.slack_alerter_ask_step.slack_alerter_post_step)
is the only available alerter integration, but it is straightforward to 
extend ZenML and build an alerter for other chat services, as shown 
[here](https://docs.zenml.io/extending-zenml/alerters).

## Send alerts in your pipelines

To send alerts in your pipelines, you first need to register an alerter
component using `zenml alerter register <MY_ALERTER>` and then add it to your 
stack with `zenml stack register ... -al <MY_ALERTER>`.

Afterward, you can import the integrations alerter steps and use them in
your pipeline.

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
[slack_alert example](https://github.com/zenml-io/zenml/tree/main/examples/slack_alert),
where we first send the test accuracy of a model to Slack and then wait with
model deployment until a user approves it in Slack.
