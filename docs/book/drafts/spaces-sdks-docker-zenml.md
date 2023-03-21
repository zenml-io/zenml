# ZenML on Spaces

[ZenML](https://github.com/zenml-io/zenml) is an extensible, open-source MLOps framework for creating portable, production-ready MLOps pipelines. It's built for Data Scientists, ML Engineers, and MLOps Developers to collaborate as they develop to production.

ZenML offers a simple and flexible syntax, is cloud- and tool-agnostic, and has
interfaces/abstractions catered toward ML workflows. With ZenML you'll have all
your favorite tools in one place, so you can tailor a workflow that caters to
your specific needs.

This Huggingface Space allows you to get up and running with a deployed version
of ZenML with just a few clicks. Within a few minutes, you'll have this default
ZenML dashboard deployed and ready for you to connect to from your local
machine.

![ZenML on HuggingFace Spaces -- default deployment](hf_spaces_chart.png)

Visit [the ZenML documentation](https://docs.zenml.io/) to learn more about its
features and how to get started with running your machine learning pipelines
through your Huggingface Spaces deployment. You can check out [some small sample
examples](https://github.com/zenml-io/zenml/tree/main/examples) of ZenML pipelines to get started or take your pick of some more
complex production-grade projects at [the ZenML Projects
repository](https://github.com/zenml-io/zenml-projects). ZenML integrates with
many of your favorite tools out of the box, [including
Huggingface](https://zenml.io/integrations/huggingface) of course! If there's
something else you want to use, we're built to be extensible and you can easily
make it work with whatever your custom tool or workflow is.

In the next sections, you'll learn to deploy your own Argilla app and use it for data labelling workflows right from the Hub. This Argilla app is a **self-contained application completely hosted on the Hub using Docker**. The diagram below illustrates the complete process.

## ⚡️ Deploy ZenML on Spaces

You can deploy ZenML on Spaces with just a few clicks:

<a  href="https://huggingface.co/new-space?template=zenml/zenml-template-space">
    <img src="https://huggingface.co/datasets/huggingface/badges/raw/main/deploy-to-spaces-lg.svg" />
</a>

To set up your ZenML app, you need to specify three main components: the Owner
(either your personal account or an organization), a Space name, and the
Visibility (a bit lower down the page). Note that the space visibility needs to
be set to 'Public' if you wish to connect to the ZenML server from your local
machine.

PHOTO GOES HERE

You have the option here to select a higher tier machine to use for your server.
The advantage of selecting a paid CPU instance is that it is not subject to
auto-shutdown policies and thus will stay up as long as you leave it up. In
order to make use of a persistent CPU, you'll likely want to create and set up a
MySQL database to connect to (see below).

To personalize your Space's appearance, such as the title, emojis, and colors,
navigate to "Files and Versions" and modify the metadata in your README.md file.
Full information on Spaces configuration parameters can be found on the
HuggingFace [documentation reference guide](https://huggingface.co/docs/hub/spaces-config-reference).

After creating your Space, you'll notice a 'Building' status along with logs
displayed on the screen. When this switches to 'Running', your Space is ready for use. If the
ZenML login UI isn't visible, try refreshing the page.

Use our default login to access the dashboard (username: 'default', password:
(leave it empty)).

## Connecting to your ZenML Server from your Local Machine

Once you have your ZenML server up and running, you can connect to it from your
local machine. To do this, you'll need to get your Space's URL.

{% hint style="warning" %}
Your Space's URL will only be available and usable for connecting from your
local machine if the visibility of the space is set to 'Public'.
{% endhint %}

In the upper-right hand corner of your space you'll see a button with three dots
which, when you click on it, will offer you a menu option to "Embed this Space".
(See [the HuggingFace
documentation](https://huggingface.co/docs/hub/spaces-embed) for more details on
this feature.) Copy the "Direct URL" shown in the box that you can now see on
the screen. This should look something like this:
`https://<YOUR_USERNAME>-<SPACE_NAME>.hf.space`.

You can now use this URL to connect to your ZenML server from your local machine
with the following CLI command (after installing ZenML, and using your custom
URL instead of the placeholder):

```shell
zenml connect --url '<YOUR_HF_SPACES_DIRECT_URL>' --no-verify-ssl --username='default'
```

You can also use the Direct URL in your browser to use the ZenML dashboard as a
fullscreen application (i.e. without the HuggingFace Spaces wrapper around it).

## Extra Configuration Options

By default the ZenML application will be configured to use a SQLite
non-persistent database. If you want to use a persistent database, you can
configure this by amending the `Dockerfile` in your Space's root directory. For
full details on the various parameters you can change, see [our reference
documentation](./docker.md#zenml-server-configuration-options) on configuring
ZenML when deployed with Docker.

{% hint style="info" %}
If you are using the space just for testing and experimentation, you don't need
to make any changes to the configuration. Everything will work out of the box.
{% endhint %}

You can also use an external secrets backend together with your HuggingFace
Spaces as described in [our
documentation](./docker.md#zenml-server-configuration-options). You should be
sure to use HuggingFace's inbuilt 'Repository secrets' functionality to
configure any secrets you need to use in your`Dockerfile` configuration. [See the
documentation](https://huggingface.co/docs/hub/spaces-sdks-docker#secret-management)
for more details how to set this up.

{% hint style="warning" %}
If you wish to use a cloud secrets backend together with ZenML for secrets
management, **you must update your password** on your ZenML Server on the
Dashboard. This is because the default user created by the
HuggingFace Spaces deployment process has no password assigned to it and as the
Space is publicly accessible (since the Space is public) *potentially anyone
could access your secrets without this extra step*. To change your password
navigate to the Settings page by clicking the button in the upper right hand
corner of the Dashboard and then click 'Update Password'.
{% endhint %}


## Upgrading your ZenML Server on HF Spaces

The default space will use the latest version of ZenML automatically. If you
want to update your version, you can simply select the 'Factory reboot' option
within the 'Settings' tab of the space. Note that this will wipe any data
contained within the space and so if you are not using a MySQL persistent
database (as described above) you will lose any data contained within your ZenML
deployment on the space. You can also configure the space to use an earlier
version by updating the `Dockerfile`'s `FROM` import statement at the very top.

## Next Steps

As a next step, check out our [ZenBytes Tutorial
series](https://github.com/zenml-io/zenbytes) which is a series of short
practical MLOps lessons through ZenML and its various integrations. It is
intended for people looking to learn about MLOps generally, and also for ML
practitioners who want to get started with ZenML. All the tutorials can be run
using Colab or with local Jupyter Notebooks.

## 🤗 Feedback and support

If you are having trouble with your ZenML server on HuggingFace Spaces, you can
view the logs by clicking on the "Open Logs" button at the top of the space.
This will give you more context of what's happening with your server.

If you have suggestions or need specific support for anything else which isn't
working, please [join the ZenML Slack community](https://zenml.io/slack-invite/)
and we'll be happy to help you out.
