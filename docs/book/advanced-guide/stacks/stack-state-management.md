---
description: How to start, stop, provision, and deprovision stacks and stack components
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Managing Stack Component States

Some stack components come with built-in daemons for connecting to the
underlying remote infrastructure. These stack components expose 
functionality for provisioning, deprovisioning, starting, or stopping the 
corresponding daemons.

{% hint style="info" %}
See the advanced section on [Services](manage-external-services.md) for more 
information on daemons.
{% endhint %}

{% hint style="warning" %}
As we move towards a more efficient and scalable stack and stack components 
management, it has become clear that the current provision and deprovision 
commands are not sufficient to allow more modularity when using different stack
components and tools. Therefore, we are deprecating the `zenml stack up` and
`zenml stack down` commands in favor of the new `zenml stack recipe pull` and
`zenml stack recipe deploy` commands. The new commands with the ZenML stack
recipes offer a more granular approach to managing stack components, allowing 
for greater control over each component's state and configuration. 
Additionally, this approach makes it easier to add new components to the stack 
and update existing ones, making the overall deployment and test process more 
streamlined and efficient. 

We will continue to support the old commands for the time being, but we
strongly recommend adding your custom stack component provisioning and
deprovisioning logic to the terraform recipe files. Alternatively, you can make 
it independent from the main implementation of the stack component. 
{% endhint %}

## Defining States of Custom Components

By default, each stack component is assumed to be in a provisioned and running
state right after creation. However, if you want to write a custom component 
and have fine-grained control over its state, you can overwrite the 
following properties and methods of the `StackComponent` base interface to
configure the component according to your needs:

```python
class StackComponent:
    """Abstract class for all components of a ZenML stack."""
    ...
    
    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run."""
        return True

    @property
    def is_running(self) -> bool:
        """If the component is running."""
        return True

    def provision(self) -> None:
        """Provisions resources to run the component."""

    def deprovision(self) -> None:
        """Deprovisions all resources of the component."""
        
    def resume(self) -> None:
        """Resumes the provisioned resources of the component."""

    def suspend(self) -> None:
        """Suspends the provisioned resources of the component."""

    ...
```