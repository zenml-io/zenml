---
description: >-
  Run coding agents in sandboxes with SSH access and steering from the UI,
  Slack, or GitHub.
icon: robot
---

# Bots

Bots run a coding agent for your team. Every conversation with the agent is a
chat, and every chat gets its own sandbox: an isolated computer with your
repositories cloned and your setup commands run. While the agent works, you
can open an SSH session into the sandbox, send it new instructions, answer its
questions, and stop it.

Bots work on ZenML Pro data. You sign in with your ZenML Pro account, and
everything you create in Bots belongs to a ZenML Pro organization. Each
agent configuration acts as a ZenML Pro service account, so inside the sandbox
the ZenML and Kitaru CLIs and SDKs are already logged in to the workspaces that
service account can read. The agent can inspect pipeline runs, stacks, models,
and deployments in those workspaces, change code, and open a pull request with
the fix.

## Who uses Bots

| Actor | Role |
| --- | --- |
| Engineers and data scientists | Start chats, give the agent tasks, steer it while it works, review what it produced |
| Admins | Configure bots, install the Slack and GitHub apps, manage shared connectors, and control who may use which bot |

## What you can do with Bots

### Hand a task to an agent and watch it work

Start a chat with a prompt such as "Find out why the last run of the training
pipeline failed and open a pull request with a fix". You can attach files and
point the prompt at ZenML resources such as a pipeline run, a model version,
or a stack. ZenML Pro picks the bot that fits the prompt best, unless you
choose one, and starts a sandbox for the chat.

Every step the agent takes appears in the chat as it happens: its messages,
its reasoning, the commands it runs, and the tools it calls.

### Steer the agent instead of waiting for it

Send a message while the agent is working, and it joins the current turn.
Queue a message instead if it should wait until the agent finishes. Interrupt
the agent to stop its current turn. When the agent needs a decision, it asks
you a question, often with options and a recommended choice, and waits for
your answer. Before it reruns, replays, or promotes something you did not ask
for, it asks for your approval.

### Get results you can review

The agent records what it produced as artifacts: links to pull requests and
branches, ZenML pipeline runs and model versions, code changes, comparisons,
charts, files such as screenshots or reports, and suggested follow-up tasks.
It ends its work with a report that summarizes the result.

### Work from Slack and GitHub

Mention the ZenML Pro app in Slack, or `@zenml-pro` on a GitHub issue or pull
request, and a chat bound to that thread starts. Replies in the thread steer
the chat, and the agent posts its reports and questions back to the thread
with a link to the chat. When something needs your attention right away, the
agent can also ping you on Slack.

### Run agents on a schedule

Automations start a chat with a fixed prompt and bot on a cron schedule, or
whenever you run them by hand. Use them for recurring work such as a daily
check of failed pipeline runs.

### Give agents access to more tools

Connectors give bots access to external services such as GitHub, Notion,
Context7, Firecrawl, and Tavily, or to a custom MCP server that runs in the
sandbox. A connector is configured once for the organization and attached to
any number of bots. For hosted services, the agent uses the service without
ever seeing the stored credential.

## Where to go next

| Page | For whom | What you learn |
| --- | --- | --- |
| [Core concepts](bots-core-concepts.md) | Everyone | Chats, bots, environments, sandboxes, steering, artifacts, automations, channels, notifications, and connectors |
| [System architecture](bots-system-architecture.md) | Admins, platform teams | How Bots fit into ZenML Pro and how sandboxes reach external services |
| [Roles and permissions](bots-rbac.md) | Admins | Who may create, use, and manage bots and the other Bots resources |

## See also

* [Organizations](./organization.md) - the scope every Bots resource
  belongs to.
* [Workspaces](./workspaces.md) - the ZenML and Kitaru servers the agent works
  with.
* [Service accounts](./service-accounts.md) - the identity a bot acts as in
  ZenML Pro.
* [Roles & Permissions](./roles.md) - ZenML Pro roles and teams.
