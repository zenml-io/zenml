# Usage Analytics

In order to help us better understand how the community uses **ZenML**, the pip package reports _anonymized_ usage 
statistics. You can always opt-out by using the CLI command:

```bash
zenml config analytics opt-out
```

{% hint style="warning" %}
Currently, opting in and out of analytics is a global setting applicable to all ZenML repositories within your system.
{% endhint %}

## Why ZenML collects analytics <a href="motivation" id="motivation"></a>

In addition to the community at large, **ZenML** is created and maintained by a startup based in Munich, Germany 
called [ZenML GmbH](https://zenml.io). We're a team of techies that love MLOps and want to build tools that 
fellow developers would love to use in their daily work. [This is us](https://zenml.io/team/), if you want to 
put faces to the names!

However, in order to improve **ZenML** and understand how it is being used, we need to use analytics to have an 
overview of how it is used 'in the wild'. This not only helps us find bugs but also helps us prioritize features 
and commands that might be useful in future releases. If we did not have this information, all we really get is 
pip download statistics and chatting with people directly, which while being valuable, is not enough to seriously 
better the tool as a whole.

## How ZenML collects these statistics <a href="implementation" id="implementation"></a>

**ZenML** uses [`Segment`](https://segment.com) as the data aggregation library for all our analytics. The entire 
code is entirely visible and can be seen at [`zenml_analytics.py`](../../../zenml/utils/zenml\_analytics.py). The 
main function is the [`track`](../../../zenml/utils/zenml\_analytics.py#L167) function that triggers 
a [Segment Analytics Track event](https://segment.com/docs/connections/spec/track/), which runs on a separate 
background thread from the main thread.

None of the data sent can identify you individually but allows us to understand how **ZenML** is being used 
holistically.

## What does ZenML collect? <a href="what" id="what"></a>

**ZenML** triggers an asynchronous [Segment Track Event](https://segment.com/docs/connections/spec/track/) on the 
following events, which is also viewable in the [`zenml_analytics.py`](../../../src/zenml/utils/analytics_utils.py) 
file in the GitHub repository.

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

# Stack
REGISTERED_STACK = "Stack registered"
SET_STACK = "Stack set"

# Analytics opt in and out
OPT_IN_ANALYTICS = "Analytics opt-in"
OPT_OUT_ANALYTICS = "Analytics opt-out"

# Examples
RUN_EXAMPLE = "Example run"
PULL_EXAMPLE = "Example pull"

# Integrations
INSTALL_INTEGRATION = "Integration installed"
```

In addition, each Segment Track event collects the following metadata:

* A unique UUID that is anonymous.
* The **ZenML** version.
* Operating system information, e.g. Ubuntu Linux 16.04
