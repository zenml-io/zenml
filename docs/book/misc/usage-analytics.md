---
description: What are the usage statistics ZenML collects
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Usage Analytics

In order to help us better understand how the community uses **ZenML**, the pip
package reports _anonymized_ usage statistics. You can always opt-out by using
the CLI command:

```bash
zenml config analytics opt-out
```

{% hint style="warning" %} Currently, opting in and out of analytics is a global
setting applicable to all ZenML repositories within your system. {% endhint %}

## Why ZenML collects analytics <a href="motivation" id="motivation"></a>

In addition to the community at large, **ZenML** is created and maintained by a
startup based in Munich, Germany called [ZenML GmbH](https://zenml.io). We're a
team of techies that love MLOps and want to build tools that fellow developers
would love to use in their daily work. [This is us](https://zenml.io/company#CompanyTeam), if
you want to put faces to the names!

However, in order to improve **ZenML** and understand how it is being used, we
need to use analytics to have an overview of how it is used 'in the wild'. This
not only helps us find bugs but also helps us prioritize features and commands
that might be useful in future releases. If we did not have this information,
all we really get is pip download statistics and chatting with people directly,
which while being valuable, is not enough to seriously better the tool as a
whole.

## How ZenML collects these statistics <a href="implementation" id="implementation"></a>

**ZenML** uses [`Segment`](https://segment.com) as the data aggregation library
for all our analytics. The entire code is entirely visible and can be seen at
[`zenml_analytics.py`](../../../src/zenml/utils/analytics_utils.py). The main
function is the [`track`](../../../src/zenml/utils/analytics_utils.py#L167) function
that triggers a
[Segment Analytics Track event](https://segment.com/docs/connections/spec/track/),
which runs on a separate background thread from the main thread.

None of the data sent can identify you individually but allows us to understand
how **ZenML** is being used holistically.

## What does ZenML collect? <a href="what" id="what"></a>

**ZenML** triggers an asynchronous
[Segment Track Event](https://segment.com/docs/connections/spec/track/) on the
following events, which is also viewable in the
[`zenml_analytics.py`](https://github.com/zenml-io/zenml/blob/main/src/zenml/utils/analytics_utils.py) file in the
GitHub repository.

```python
# Pipelines
RUN_PIPELINE = "Pipeline run"
GET_PIPELINES = "Pipelines fetched"
GET_PIPELINE = "Pipeline fetched"

# Repo
INITIALIZE_REPO = "ZenML initialized"

# Profile
INITIALIZED_PROFILE = "Profile initialized"

# Components
REGISTERED_STACK_COMPONENT = "Stack component registered"
UPDATED_STACK_COMPONENT = "Stack component updated"
COPIED_STACK_COMPONENT = "Stack component copied"

# Stack
REGISTERED_STACK = "Stack registered"
REGISTERED_DEFAULT_STACK = "Default stack registered"
SET_STACK = "Stack set"
UPDATED_STACK = "Stack updated"
COPIED_STACK = "Stack copied"
IMPORT_STACK = "Stack imported"
EXPORT_STACK = "Stack exported"

# Model Deployment
MODEL_DEPLOYED = "Model deployed"

# Analytics opt in and out
OPT_IN_ANALYTICS = "Analytics opt-in"
OPT_OUT_ANALYTICS = "Analytics opt-out"

# Examples
RUN_ZENML_GO = "ZenML go"
RUN_EXAMPLE = "Example run"
PULL_EXAMPLE = "Example pull"

# Integrations
INSTALL_INTEGRATION = "Integration installed"

# Users
CREATED_USER = "User created"
CREATED_DEFAULT_USER = "Default user created"
DELETED_USER = "User deleted"

# Teams
CREATED_TEAM = "Team created"
DELETED_TEAM = "Team deleted"

# Projects
CREATED_PROJECT = "Project created"
DELETED_PROJECT = "Project deleted"

# Role
CREATED_ROLE = "Role created"
DELETED_ROLE = "Role deleted"

# Flavor
CREATED_FLAVOR = "Flavor created"

# Test event
EVENT_TEST = "Test event"

# Stack recipes
PULL_STACK_RECIPE = "Stack recipes pulled"
RUN_STACK_RECIPE = "Stack recipe created"
DESTROY_STACK_RECIPE = "Stack recipe destroyed"
```
Each Segment Track event collects the following metadata:

- A unique UUID that is anonymous.
- The **ZenML** version.
- Operating system information, e.g. Ubuntu Linux 16.04

In addition, if you have opted-in to email communication (e.g. via `zenml go` or 
the email collection screen on the dashboard), then the `email` is sent as a metadata 
field.

## If I share my email, will you spam me?

No, we won't. Our sole purpose of contacting you will be to ask for feedback (e.g. in the 
shape of a user interview). These interviews help the core team understand usage better, 
and prioritize feature requests.

If you have any concerns about data privacy and usage of personal information, please 
[contact us](mailto:support@zenml.io) and we will try to alleviate any concerns as soon 
as possible.

