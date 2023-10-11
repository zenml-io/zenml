---
description: How to add users to your ZenML deployment
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Multi-player mode with ZenML

After you have [deployed ZenML](../../getting-started/deploying-zenml/deploying-zenml.md) and [connected your local client with the deployment](./zenml-deployment.md), you can go ahead and start adding your teammates as users.

By default, all users have `Administrator` permissions throughout the ZenML dashboard, however one user can always choose to [share](../stacks/managing-stacks.md#sharing-stacks-over-a-zenml-server) or not share their stacks.

## Personal Settings

You can go to the settings page from the bottom of the side bar or top right of the header, and edit your details below:

![Personal Settings](../../assets/starter_guide/collaboration/01_personal_settings.png)

## Workspace Settings

![Workspace Settings](../../assets/starter_guide/collaboration/02_project_settings.png)

In project settings, you can see a list of users who are invited or signed up for this ZenML deployment. You can go ahead and invite a new user here with a
unique username. The dashboard will generate a new token for you, in the form of a URL that you can copy and send to your teammate.

![Invite Token](../../assets/starter_guide/collaboration/03_invite_token.png)

You can also mimic this behavior in a connected ZenML with the following commands:

```shell
zenml user create USERNAME
```

This creates a new user. If an empty password is configured, an activation token is generated and a link to the dashboard is provided where the user can sign up.
d
## Sign up

From the invitation URL, a user can sign up as expected:

![Sign up](../../assets/starter_guide/collaboration/04_sign_up.png)

And that's it 🚀. We went from a simple ZenML pip install to a fully fledged multi-user, cloud deployment of ZenML.

Now, the next steps are to create stacks with [components from the component gallery](../../component-gallery/categories.md), or dive into
[advanced topics](../../advanced-guide/pipelines/pipelines.md) to learn about the inner workings of ZenML!