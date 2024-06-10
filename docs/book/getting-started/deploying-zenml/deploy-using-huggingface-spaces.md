---
description: Deploying ZenML to Huggingface Spaces.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy using HuggingFace Spaces

A quick way to deploy ZenML and get started is to use [HuggingFace Spaces](https://huggingface.co/spaces). HuggingFace Spaces is a platform for hosting and sharing ML projects and workflows, and it also works to deploy ZenML. You can be up and running in minutes (for free) with a hosted ZenML server, so it's a good option if you want to try out ZenML without any infrastructure overhead.

{% hint style="info" %}
Note that it is not recommended to use HuggingFace Spaces for production use as by default the data stored there is non-persistent and the underlying machine is not as available to you as a dedicated machine. See our [other deployment options](./README.md) if you want to use ZenML in production.
{% endhint %}

![ZenML on HuggingFace Spaces -- default deployment](../../../.gitbook/assets/hf\_spaces\_chart.png)

In this diagram, you can see what the default deployment of ZenML on HuggingFace looks like.

## Deploying ZenML on HuggingFace Spaces

You can deploy ZenML on HuggingFace Spaces with just a few clicks:

[![](https://huggingface.co/datasets/huggingface/badges/raw/main/deploy-to-spaces-lg.svg)](https://huggingface.co/new-space?template=zenml/zenml)

To set up your ZenML app, you need to specify three main components: the Owner (either your personal account or an organization), a Space name, and the Visibility (a bit lower down the page). Note that the space visibility needs to be set to 'Public' if you wish to connect to the ZenML server from your local machine.

![HuggingFace Spaces SDK interface](../../.gitbook/assets/hf-spaces-sdk.png)

You have the option here to select a higher-tier machine to use for your server. The advantage of selecting a paid CPU instance is that it is not subject to auto-shutdown policies and thus will stay up as long as you leave it up. In order to make use of a persistent CPU, you'll likely want to create and set up a MySQL database to connect to (see below).

To personalize your Space's appearance, such as the title, emojis, and colors, navigate to "Files and Versions" and modify the metadata in your README.md file. Full information on Spaces configuration parameters can be found on the HuggingFace [documentation reference guide](https://huggingface.co/docs/hub/spaces-config-reference).

After creating your Space, you'll notice a 'Building' status along with logs displayed on the screen. When this switches to 'Running', your Space is ready for use. If the ZenML login UI isn't visible, try refreshing the page.

In the upper-right hand corner of your space you'll see a button with three dots which, when you click on it, will offer you a menu option to "Embed this Space". (See [the HuggingFace documentation](https://huggingface.co/docs/hub/spaces-embed) for more details on this feature.) Copy the "Direct URL" shown in the box that you can now see on the screen. This should look something like this: `https://<YOUR_USERNAME>-<SPACE_NAME>.hf.space`. Open that URL and follow the instructions to initialize your ZenML server and set up an initial admin user account.

## Connecting to your ZenML Server from your local machine

Once you have your ZenML server up and running, you can connect to it from your local machine. To do this, you'll need to get your Space's 'Direct URL' (see above).

{% hint style="warning" %}
Your Space's URL will only be available and usable for connecting from your local machine if the visibility of the space is set to 'Public'.
{% endhint %}

You can use the 'Direct URL' to connect to your ZenML server from your local machine with the following CLI command (after installing ZenML, and using your custom URL instead of the placeholder):

```shell
zenml connect --url '<YOUR_HF_SPACES_DIRECT_URL>'
```

You can also use the Direct URL in your browser to use the ZenML dashboard as a fullscreen application (i.e. without the HuggingFace Spaces wrapper around it).

{% hint style="warning" %}
The ZenML dashboard will currently not work when viewed from within the Huggingface webpage (i.e. wrapped in the main `https://huggingface.co/...` website). This is on account of a limitation in how cookies are handled between ZenML and Huggingface. You **must** view the dashboard from the 'Direct URL' (see above).
{% endhint %}

## Extra configuration options

By default, the ZenML application will be configured to use an SQLite non-persistent database. If you want to use a persistent database, you can configure this by amending the `Dockerfile` to your Space's root directory. For full details on the various parameters you can change, see [our reference documentation](deploy-with-docker.md#advanced-server-configuration-options) on configuring ZenML when deployed with Docker.

{% hint style="info" %}
If you are using the space just for testing and experimentation, you don't need to make any changes to the configuration. Everything will work out of the box.
{% endhint %}

You can also use an external secrets backend together with your HuggingFace Spaces as described in [our documentation](deploy-with-docker.md#advanced-server-configuration-options). You should be sure to use HuggingFace's inbuilt ' Repository secrets' functionality to configure any secrets you need to use in your`Dockerfile` configuration. [See the documentation](https://huggingface.co/docs/hub/spaces-sdks-docker#secret-management) for more details on how to set this up.

{% hint style="warning" %}
If you wish to use a cloud secrets backend together with ZenML for secrets management, **you must update your password** on your ZenML Server on the Dashboard. This is because the default user created by the HuggingFace Spaces deployment process has no password assigned to it and as the Space is publicly accessible (since the Space is public) _potentially anyone could access your secrets without this extra step_. To change your password navigate to the Settings page by clicking the button in the upper right-hand corner of the Dashboard and then click 'Update Password'.
{% endhint %}

## Troubleshooting

If you are having trouble with your ZenML server on HuggingFace Spaces, you can view the logs by clicking on the "Open Logs" button at the top of the space. This will give you more context of what's happening with your server.

If you have any other issues, please feel free to reach out to us on our [Slack channel](https://zenml.io/slack/) for more support.

## Upgrading your ZenML Server on HF Spaces

The default space will use the latest version of ZenML automatically. If you want to update your version, you can simply select the 'Factory reboot' option within the 'Settings' tab of the space. Note that this will wipe any data contained within the space and so if you are not using a MySQL persistent database (as described above) you will lose any data contained within your ZenML deployment on the space. You can also configure the space to use an earlier version by updating the `Dockerfile`'s `FROM` import statement at the very top.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
