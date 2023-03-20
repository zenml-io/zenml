---
description: Deploying ZenML to Huggingface Spaces
---

A quick way to deploy ZenML and get started is to use [HuggingFace Spaces](https://huggingface.co/spaces).
HuggingFace Spaces is a platform for hosting and sharing ML projects and
workflows, and it also works to deploy ZenML. You can be up and running in
minutes (for free) with a hosted ZenML server so it's a good option if you want
to try out ZenML without any infrastructure overhead.

{% hint style="info" %}
Note that it is not recommended to use HuggingFace Spaces for production use as
by default the data stored there is non-persistent and the underlying machine is
not as available to you as a dedicated machine. See our [other deployment options](./deploying-zenml.md)
if you want to use ZenML in production.
{% endhint %}


## Deploying ZenML to HuggingFace Spaces

You can deploy ZenML on HuggingFace Spaces with just a few clicks:

BUTTON GOES HERE

To set up your ZenML app, you need to specify three main components: the Owner
(either your personal account or an organization), a Space name, and the
Visibility (a bit lower down the page). Note that the space visibility needs to
be set to 'Public' if you wish to connect to the ZenML server from your local machine.

You have the option here to select a higher tier machine to use for your server.
The advantage of selecting a paid CPU instance is that it is not subject to
auto-shutdown policies and thus will stay up as long as you leave it up. In
order to make use of a persistent CPU, you'll likely want to create and set up a
MySQL database to connect to (see below).

To personalize your Space's appearance, such as the title, emojis, and colors, navigate to "Files and Versions" and modify the metadata in your README.md file.

After creating your Space, you'll notice a 'Building' status along with logs
displayed on the screen. When this switches to 'Running', your Space is ready for use. If the
ZenML login UI isn't visible, try refreshing the page.

Use our default login to access the dashboard (username: 'default', password:
(leave it empty)).

## Extra Configuration Options

## Troubleshooting

## Upgrading your ZenML Server on HF Spaces


