---
description: Learning about the ZenML server.
---

# Switch to production

When you first get started with ZenML, it is based on the following architecture on your machine:

![Scenario 1: ZenML default local configuration](../../.gitbook/assets/Scenario1.png)

The SQLite database that you can see in this diagram is used to store all the metadata we produced in the previous guide (pipelines, models, artifacts) etc.

In order to move into production, you will need to deploy this server somewhere centrally outside of your machine. This allows different infrastructure components to interact with, alongside enabling you to collaborate with your team members:

![Scenario 3: Deployed ZenML Server](../../.gitbook/assets/Scenario3.2.png)


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>