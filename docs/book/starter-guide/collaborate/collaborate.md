---
description: How to collaborate with your team in ZenML
---

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

## Centralized ZenML Management with ZenML Server


## Step 1: Single user working with local stacks

![Working with local ZenML](../../assets/starter_guide/collaboration/01_local_stack.png)

## Step 2: Single user working with local and cloud stacks

![Single user working with local and cloud stacks](../../assets/starter_guide/collaboration/02_multiple_stacks.png)

## Step 3: Multiple users working with local and cloud stacks

![Multiple users working with local and cloud stacks](../../assets/starter_guide/collaboration/03_multiple_users.png)

## Collaboration with ZenML Overview

![Collaboration with ZenML Overview](../../assets/starter_guide/collaboration/04_cloud_collaboration_overview.png)

