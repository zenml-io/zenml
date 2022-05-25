# ⏭ Send alerts to Slack from within your ZenML pipelines

This example showcases how to use the ZenML `Slack` integration to send alerts
to one of your Slack channels as part of your ML pipelines.
The integration includes an `alerter` component, as well as a standard step
that takes a string as input and post it to slack according to the alerter
configuration.

This is very useful in practice so you can get notified immediately when 
failures happen, and also for general monitoring / reporting.

The following is a very simple example where we build a pipeline that trains 
and evaluates an sklearn SVC model on the digits datasets and posts the test 
accuracy to Slack.

## 🖥 Run it locally

### 📄 Prerequisites

In order to run this example, you need to have a Slack workspace set up
with a channel that you want your pipelines to post to.
Open the channel in a browser, then copy out the last part of the URL 
('C....').
This is the `<SLACK_CHANNEL_ID>` you will need when registiering the
slack alerter component.

Then, you need to [create a Slack App](https://api.slack.com/apps?new_app=1)
with a bot in your workspace.
Under `OAuth & Permissions` you can find the `<SLACK_TOKEN>` of your bot,
which you will need later when defining the slack alerter stack component.
Also, under `Scopes` in the `OAuth & Permissions` tab, give your
bot `chat:write` and `chat:write.public` permissions.

Now you can get started with this example. 
Run the following code to install and initialize ZenML and create the stack.
Make sure to replace `<SLACK_TOKEN>` and `<SLACK_CHANNEL_ID>` first.

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install sklearn slack -y

# pull example
zenml example pull slack_alert
cd zenml_examples/slack_alert

# initialize
zenml init

# create and enter a new ZenML profile
zenml profile create slack_example
zenml profile set slack_example

# register slack alerter
zenml alerter register slack_alerter -f slack --slack_token=<SLACK_TOKEN> --default_slack_channel_id=<SLACK_CHANNEL_ID>

# register new stack with slack alerter and set it active
zenml stack register slack_stack -o default -m default -a default -al slack_alerter
zenml stack set slack_stack
```

### ▶️ Run the Code

Now we're ready. Execute:

```shell
python run.py
```

You should see the following output in your slack channel:

![TSlack Message Posted](assets/slack-message.png)

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```


# 📜 Learn more

If you want to learn more about alerters in zenml in general or about how to build your own alerter steps in zenml
check out our [docs](https://docs.zenml.io/extending-zenml/alerter).
