---
description: >-
  Control who can create, use, share, and manage bots, environments,
  automations, channels, and connectors with ZenML Pro roles.
icon: lock
---

# Roles and permissions

Bots use the [roles and permissions](roles.md) of ZenML Pro. You sign in to
Bots with your ZenML Pro account, every Bots resource belongs to a ZenML Pro
organization, and ZenML Pro roles decide which actions you may perform.
You manage access to Bots in the same place as access to the rest of your
organization.

This page explains who can sign in, which Bots resources are protected, what
the owner of a resource can do, how to grant access to others, and what you
see when a request is denied. For the resources themselves, see
[Core concepts](bots-core-concepts.md).

## Signing in

Bots accept two kinds of ZenML Pro credentials:

* **Your ZenML Pro session.** When you open the Bots UI, you sign in to the
  organization you choose. A Bots session lasts one hour.
* **A ZenML Pro API key**, for example the API key of a
  [service account](service-accounts.md). Pass it to the Python SDK together
  with the organization. When you call the REST API directly, send the key as
  a bearer token together with the organization.

To sign in to an organization, your account must be able to read that
organization in ZenML Pro. The owner of the organization and every member
with the Organization Admin, Organization Manager, Organization Viewer, or
Organization Member role can sign in. A member whose only role is Billing
Admin cannot.

## Organizations and workspaces

Every Bots resource belongs to exactly one organization, and a Bots session
works in one organization at a time. Resources of another organization are
never visible. They are reported as not found, even when you have access to
that other organization.

Bots resources do not belong to a [workspace](workspaces.md), so workspace
and project roles do not grant any access to them. Workspaces come into play
through the ZenML Pro service account each bot acts as. The agent in a
sandbox can reach exactly the workspaces and projects that this service
account can reach.

## The service account of a bot

Creating a bot also creates a [service account](service-accounts.md) for it
with the predefined **Bot** role. This role lets the service account view and
create resources in a workspace and all of its projects. The agent uses this
service account for every ZenML Pro request it makes from the sandbox, so it
acts with the permissions of the bot and not with those of the user who
started the chat.

For more control over what a bot can reach, assign
[custom roles](roles.md) to its service account, the same way as for any
other service account.

## Protected resources and actions

Permissions apply to five resource types:

| Resource | Actions | Notes |
| --- | --- | --- |
| Bot | `create`, `read`, `use`, `update`, `delete` | `use` starts and continues chats with the bot |
| Environment | `create`, `read`, `update`, `delete` | Access to a bot also grants access to its environment |
| Automation | `read`, `update`, `delete` | Creating an automation requires `use` on its bot |
| Channel | `create`, `update`, `delete` | Every member of the organization can see the channels |
| Connector | `create`, `update`, `delete` | Every member of the organization can see the connectors |

Chats and everything in them, such as messages, events, artifacts, feedback,
and SSH access, have no permissions of their own. Access to a chat follows from the bot of the chat, as described in
[Chats](#chats).

Linked Slack and GitHub identities are private. You can only see, create,
change, and remove the links of your own account, including which one is your
notification target.

## Ownership

The account that creates a resource owns it. The owner of a bot, environment,
automation, channel, or connector can always perform every action on it,
whatever roles they hold. The owner of a resource does not change later.

Chats are the one exception. The owner of a chat can always read it, but
continuing the chat runs the bot again, so it requires `use` on the bot. See
[Chats](#chats).

## Granting access with roles

A ZenML Pro role permission on a Bots resource type, such as `use` on `bot`,
applies to every resource of that type in the organization.

Out of the box, only **Organization Admin** grants Bots permissions. An
Organization Admin can perform every action on every Bots resource in the
organization. The other predefined organization roles grant none. Members
with those roles can sign in, see channels and connectors, and work with the
resources they own or that were shared with them, but they cannot create any
Bots resource.

To give members broader Bots access without making them Organization
Admins, create a custom organization role that holds permissions on the
resource types `bot`, `environment`, `automation`, `channel`, and `connector`,
and assign it to users or [teams](teams.md). Custom organization roles are
created through the ZenML Pro API, as described in
[Custom Roles](roles.md#custom-roles). A role that lets a team use every bot
but manage none of them, for example, holds `read` and `use` on `bot`.

For bots, a higher action includes the lower ones:

| Granted action | Also grants |
| --- | --- |
| `update` | `use`, `read` |
| `use` | `read` |
| `read` | Nothing else |

`create` and `delete` stand on their own. For all other resource types, each
action grants only itself.

## Sharing bots

To give someone access to one bot instead of every bot, share it with a
ZenML Pro user or [team](teams.md). You can share the actions `read`, `use`,
and `update`. Bots are the only resource you can share, and `create` and
`delete` cannot be shared.

The following rules apply when you share a bot:

* To grant an action, you need that action on the bot yourself. The owner of
  the bot can grant every shareable action.
* To revoke an action, you need `update` on the bot. A member who only holds
  `use` cannot revoke the access of others.
* To share with a team, you need to be able to see that team in ZenML Pro.
* You cannot share a bot with yourself.

Deleting a bot removes every share on it.

Share a bot from its page in the Bots UI. To share a bot from the Python SDK
or the REST API, update the members of the bot with the user or team and the
actions to add or remove.

## What each operation requires

### Bots

| Operation | Required |
| --- | --- |
| Create a bot | `create` on `bot`, and `read` on the environment the bot runs in. Connectors attached at creation must belong to the organization and be configured. |
| View a bot, or list bots | `read` on the bot. Lists contain only the bots you can read. |
| Change a bot, archive it, or attach or detach a connector | `update` on the bot. Moving the bot to another environment also requires `read` on that environment. |
| Delete a bot | `delete` on the bot |

### Chats

| Operation | Required |
| --- | --- |
| Start a chat with a chosen bot | `use` on the bot |
| Start a chat and let ZenML Pro pick the bot | `use` on at least one bot. Only the bots you can use are considered. |
| View a chat, its messages, events, and artifacts, or give feedback | Ownership of the chat, or `read` on its bot |
| Send a message, retry or discard a failed message, or rename, archive, pause, resume, or interrupt a chat | `use` on its bot |
| Request SSH access | `use` on its bot |
| Create or delete an artifact | `use` on its bot |

The chat list contains your own chats and the chats of every bot you can
read.

### Environments

| Operation | Required |
| --- | --- |
| Create an environment | `create` on `environment` |
| View an environment or its snapshots | `read` on the environment, or `read` on a bot that runs in it |
| Change an environment or build a snapshot | `update` on the environment, or `update` on a bot that runs in it |
| Delete an environment | `delete` on the environment |

The values of secret environment variables are never returned. Responses only
list their names.

### Automations

| Operation | Required |
| --- | --- |
| Create an automation | `use` on its bot |
| View an automation, its triggers, or its runs | `read` on the automation, or `read` on its bot |
| Change an automation, or create, change, or delete a trigger | `update` on the automation. Moving the automation to another bot also requires `use` on that bot. |
| Run an automation by hand | `read` on the automation and `use` on its bot |
| Delete an automation | `delete` on the automation |

A run you start by hand creates a chat that you own. A scheduled run creates
a chat owned by the owner of the automation, so the owner needs `use` on the
bot for scheduled runs to start.

### Channels

| Operation | Required |
| --- | --- |
| View channels | Membership in the organization |
| Install the Slack or GitHub app | `create` on `channel`, which only Organization Admins have by default. Reinstalling into a Slack workspace that is already installed also requires `update` on that channel. A GitHub installation also requires that you own the GitHub user account or are an owner of the GitHub organization. |
| List the repositories of the GitHub installations | Membership in the organization |
| Change a channel | `update` on the channel |
| Uninstall a channel | `delete` on the channel |

### Connectors

| Operation | Required |
| --- | --- |
| View connectors | Membership in the organization |
| Create a connector | `create` on `connector` |
| Change, test, or authorize a connector | `update` on the connector |
| Delete a connector | `delete` on the connector |
| Attach a connector to a bot, or detach it | `update` on the bot |

The stored credential of a connector is never returned.

### Attachments

Only the user who uploaded a file can attach it to a prompt. Downloading an
attachment requires `read` on the chat or automation it belongs to.

## Slack and GitHub

Messages in Slack and on GitHub run as the ZenML Pro user who sent them. To
use Bots from Slack or GitHub, link your Slack or GitHub account to your ZenML
Pro account on the connections page of the ZenML Pro dashboard settings. Service
accounts cannot link an identity.

The same permissions apply as in the UI:

* A message from an unlinked user does not reach the agent. The ZenML Pro
  app replies with a link to the page where they can link their account. In
  Slack, only the sender sees this reply. On GitHub, the app posts it once per
  user and thread as a comment that mentions the sender.
* Starting a chat in a thread requires `use` on at least one bot. Only the
  bots the sender can use are considered.
* Replying in the thread of an existing chat requires `use` on the bot of
  that chat, also for the user who started it. Anyone in the thread who lacks
  that permission has their message dropped, and the app posts the reason in
  the thread.

## The agent in the sandbox

The agent in a sandbox does not act as a user. It can only work on its own
chat, for example to add artifacts or notify the owner of the chat. It cannot
read or change any other chat or Bots resource.

Connectors follow the bot of the chat. A sandbox only receives the
credentials of connectors attached to its bot, and the agent never sees the
stored credential itself, except for the API key of a custom MCP server. See
[Credentials Stay Outside the Sandbox](bots-system-architecture.md#credentials-stay-outside-the-sandbox).

## When access is denied

| Situation | Response | Example message |
| --- | --- | --- |
| No credential, or a credential ZenML Pro rejects | `401 Unauthorized` | `Invalid control plane credential.` |
| An action you may not perform on one resource | `403 Forbidden` | `Not permitted to update bot <bot-id>` |
| An action you may not perform on any resource of a type | `403 Forbidden` | `Not permitted to create environments` |
| A chat operation that needs an action on the chat's bot | `403 Forbidden` | `Not permitted to use chat <chat-id>. Requires use on bot <bot-id>` |
| A resource of another organization | `404 Not Found` | |
| An invalid share, such as a share with yourself | `422 Unprocessable Entity` | `Sharing with the caller is not allowed` |
| ZenML Pro cannot be reached for a permission check | `503 Service Unavailable` | `Control plane permission check failed.` |

The Python SDK raises `AuthenticationError` for `401`, `AuthorizationError`
for `403`, `NotFoundError` for `404`, `ValidationError` for `422`, and
`ServerError` for `503`.

When ZenML Pro cannot be reached, the request is denied instead of allowed. Lists of bots, environments, automations, chats, and artifacts
leave out every resource you cannot read, so a resource missing from one of
these lists may be one you have no access to.

## Related documentation

* [Bots](bots.md)
* [Core concepts](bots-core-concepts.md)
* [System architecture](bots-system-architecture.md)
* [Roles & Permissions](roles.md)
* [Teams](teams.md)
* [Service Accounts](service-accounts.md)
* [Organizations](organization.md)

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
