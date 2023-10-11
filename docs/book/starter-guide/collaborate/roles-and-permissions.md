---
description: How roles and permissions work within ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}

{% hint style="warning" %}
Permissions and roles are an alpha feature of ZenML and are in active 
development.
{% endhint %}

# Permissions

The following global permissions are available within ZenML.

**read**: Read permission on all resources.
**write**: Write permission on all resources.
**me**: Permission for a user to edit their own user metadata
(username, password, etc.)

To view the available permissions through the CLI simply run:

`zenml permission list`

# Roles

Users are granted **Permissions** through **Roles**. You can list all roles
with their associated permissions by running.

`zenml role list`

## Default Roles

By default, ZenML comes with two roles.

**admin**: The admin role grants all permissions globally. 
(Permissions: read, write, me )

**guest**: The guest role lets users change their own user data and grants 
general global read access. (Permissions: read, me )

## Custom Roles

You can also create your own roles through the CLI:

`zenml role create <ROLE_NAME> -p read -p write -p me`

# Assigning roles to users

Roles can be assigned to users through the CLI:

`zenml role assign <ROLE_NAME> --user <USER_NAME>`

alternatively this can also be done during user creation 

`zenml user create <USER_NAME> --role <ROLE_NAME>`

{% hint style="info" %}
By default, user creation through the UI will grant the user `admin` rights. 
This default behaviour will change in the next iteration of the Dashboard as 
the role will be selectable during user creation and in the User settings menu.
{% endhint %}

# Listing active role assignments

If you want to inspect which roles have been assigned to which users, 
simply run:

`zenml role assignment list`

## Limitations

* For the time being all roles apply permissions locally. This may change in the 
future. Feel free to let us know on 
[Slack](https://zenml.slack.com/join/shared_invite/zt-t4aw242p-K6aCaUjhnxNOrLR7bcAb7g#/shared-invite/email) 
or through our 
[Roadmap](https://zenml.hellonext.co/roadmap) if this is important for you.

* Permissions and roles only become relevant if you are running through a 
[deployed ZenML Server](https://docs.zenml.io/getting-started/deploying-zenml).
In local settings with a direct connection to a SQLite Database user access is
not limited/granted by roles.