---
description: How to collaborate with your team in ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# ZenML for Teams and Organizations

Using ZenML to develop and execute pipelines from the comfortable confines of
your workstation or laptop is a great way to incorporate MLOps best practices
and production grade quality into your project from day one. However, as machine
learning projects grow, managing and running ZenML in a single-user and
single-machine setting can become a strenuous task. More demanding projects
involve creating and managing an increasing number of pipelines and complex
Stacks built on a wider and continuously evolving set of technologies. This can
easily exceed the capabilities of a single machine and person or role.

The same principles observed in the ZenML single-user experience are applicable
as a framework of collaboration between the various specialized roles in the
AI/ML team. We purposefully maintain a clean separation between the core ZenML
concepts, with the intention that they may be managed as individual
responsibilities assigned to different members of a team or department without
incurring the overhead and friction usually associated with larger
organizations.

One such example is the decoupling of ZenML Stacks from pipelines and their
associated code, a principle that provides for a smooth transition from
experimenting with and running pipelines locally to deploying them to production
environments. It is this same decoupling that also allows ZenML to be used
in a setting where part of a team is iterating on writing ML code and
implementing pipelines, while the other part is defining and actively
maintaining the infrastructure and the Stacks that will be used to execute
pipelines in production. Everyone can remain focused on their responsibilities
with ZenML acting as the central piece that connects and coordinates everything
together.

The ability to configure modular Stacks in which every component has a
specialized function is another way in which ZenML maintains a clean separation
of concerns. This allows for a MLOps Stack design that is natively flexible and
extensible that can evolve organically to match the size and structure
of your AI/ML team and organization as you iterate on your project and invest
more resources into its development.

This documentation section is dedicated to describing several ways in which you
can deploy ZenML as a collaboration framework and enable your entire AI/ML team
to enjoy its advantages.

## Export and Import ZenML Stacks

If you need to quickly share your Stack configuration with someone else, there
is nothing easier than [using the ZenML CLI to export a Stack](./stack-export-import.md)
in the form of a YAML file and import it somewhere else.

## Organize and Share with Profiles

With [ZenML Profiles](./zenml-store.md), you can unlock a range of strategies for
organizing and managing ZenML configurations that are available across your
entire team. Stacks, Stack Components and other classes of ZenML objects can be
stored in a central location and shared across multiple users, teams and
automated systems such as CI/CD processes.

## Centralized ZenML Management with ZenServer

With the [_ZenServer_](./zenml-server.md), you can deploy ZenML as a centralized
service and connect entire teams and organizations to an easy to manage
collaboration platform that provides a unified view on the MLOps processes,
tools and technologies that support your entire AI/ML project lifecycle.
