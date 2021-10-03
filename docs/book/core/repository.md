---
description: A ZenML repository the heart of your ZenML codebase.
---

# Repository

Every ZenML project starts inside a ZenML repository. Think of it just like a normal Git repository, except that there are some added bonuses on top! A repository is at the core of all ZenML activity. Every action that can be executed within ZenML must take place within a ZenML repository. ZenML repositories are inextricably tied to `git`. ZenML creates a `.zen` folder at the root of your repository to manage your assets and metadata.

To create a ZenML repository, do the following after having installed ZenML:

```text
zenml init
```

{% hint style="warning" %}
Please make sure to be inside a valid git repository before executing the above!
{% endhint %}

The initialization creates a local `.zen` folder where various information about your local configuration lives, e.g., the active [Stack](stacks.md) that you are using to run pipelines.

