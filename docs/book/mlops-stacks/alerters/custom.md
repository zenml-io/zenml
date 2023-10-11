---
description: How to develop a custom alerter
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## Base Abstraction

The base abstraction for alerters is very basic, as it only defines two
abstract methods that subclasses should implement:
- `post()` takes a string, posts it to the desired chat service, and returns 
`True` if the operation succeeded, else `False`.
- `ask()` does the same as `post()`, but after sending the message, it waits
until someone approves or rejects the operation from within the chat service
(e.g., by sending "approve" / "reject" to the bot as response).
`ask()` then only returns `True` if the operation succeeded and was approved,
else `False`.

Then base abstraction looks something like this:

```python
class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    def post(
        self, message: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service."""
        return True

    def ask(
        self, question: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service and wait for approval."""
        return True
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation.
To see the full docstrings and imports, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/alerter/base_alerter.py).
{% endhint %}

## Building your own custom alerter

Creating your own custom alerter can be done in three steps:

1. Create a class that inherits from the `BaseAlerter`.
2. Define the `FLAVOR` class variable in your class (e.g., `FLAVOR="discord"`)
3. Implement the `post()` and `ask()` methods for your alerter.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml alerter flavor register <THE-SOURCE-PATH-OF-YOUR-ALERTER>
```