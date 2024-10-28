---
icon: memo-circle-info
description: Configuring ZenML's default logging behavior
icon: memo-circle-info
---

# Control logging

ZenML produces various kinds of logs:

* The [ZenML Server](../../getting-started/deploying-zenml/) produces server logs (like any FastAPI server).
* The [Client or Runner](../configure-python-environments/#client-environment-or-the-runner-environment) environment produces logs, for example after running a pipeline. These are steps that are typically before, after, and during the creation of a pipeline run.
* The [Execution environment](../configure-python-environments/#execution-environments) (on the orchestrator level) produces logs when it executes each step of a pipeline. These are logs that are typically written in your steps using the python `logging` module.

This section talks about how users can control logging behavior in these various environments.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
