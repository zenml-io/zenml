---
description: Managing stacks
---

# Things to change

- This should serve as a lead in to the collaboration section
- It should talk about the concept shared stacks 
- Maybe mention export and import of stacks as a lead up to ZenML Server

With collaboration being the key part of ZenML, the 0.20.0 release puts the
concepts of Users and Projects front and center and introduces
the possibility to share stacks and stack components with other users by
means of the ZenML server.

When your client is connected to a ZenML server, entities such as Stacks, Stack
Components, Stack Component Flavors, Pipelines, Pipeline Runs, and Artifacts are
scoped to a Project and owned by the User that creates them. Only the objects
that are owned by the current user used to authenticate to the ZenML server and
that are part of the current project are available to the client.

Stacks and Stack Components can also be shared within the same project with
other users. To share an object, either set it as shared during creation time
(e.g. `zenml stack register mystack ... --share`) or afterwards (e.g. through
`zenml stack share mystack`).

To differentiate between shared and private Stacks and Stack Components, these
can now be addressed by name, id or the first few letters of the id in the cli.
E.g. for a stack `default` with id `179ebd25-4c5b-480f-a47c-d4f04e0b6185` you
can now run `zenml stack describe default` or `zenml stack describe 179` or
`zenml stack describe 179ebd25-4c5b-480f-a47c-d4f04e0b6185`.

We also introduce the notion of `local` vs `non-local` stack components. Local
stack components are stack components that are configured to run locally while
non-local stack components are configured to run remotely or in a cloud
environment. Consequently:

* stacks made up of local stack components should not be shared on a central
ZenML Server, even though this is not enforced by the system.
* stacks made up of non-local stack components are only functional if they
are shared through a remotely deployed ZenML Server.