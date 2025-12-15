---
description: Learning how to develop a custom alerter.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Develop a Custom Alerter

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

### Base Abstraction

The base abstraction for alerters is very basic, as it only defines two abstract methods that subclasses should implement:

* `post()` takes a string, posts it to the desired chat service, and returns `True` if the operation succeeded, else `False`.
* `ask()` does the same as `post()`, but after sending the message, it waits until someone approves or rejects the operation from within the chat service (e.g., by sending "approve" / "reject" to the bot as a response). `ask()` then only returns `True` if the operation succeeded and was approved, else `False`.

The `ask()` method is particularly useful for implementing human-in-the-loop workflows. When implementing this method, you should:
- Wait for user responses containing approval keywords (like `"approve"`, `"yes"`, `"ok"`, `"LGTM"`)
- Wait for user responses containing disapproval keywords (like `"reject"`, `"no"`, `"cancel"`, `"stop"`)
- Return `True` only when explicit approval is received
- Return `False` for disapproval, timeout, or any errors
- Consider implementing configurable approval/disapproval keywords via parameters

Then base abstraction looks something like this:

```python
from abc import ABC
from typing import Optional
from zenml.stack import StackComponent
from zenml.alerter import BaseAlerterStepParameters

class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    def post(
            self, message: str, params: Optional[BaseAlerterStepParameters]
    ) -> bool:
        """Post a message to a chat service."""
        return True

    def ask(
            self, question: str, params: Optional[BaseAlerterStepParameters]
    ) -> bool:
        """Post a message to a chat service and wait for approval."""
        return True
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation. To see the full docstrings and imports, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/alerter/base\_alerter.py).
{% endhint %}

### Building your own custom alerter

Creating your own custom alerter can be done in four steps:

1.  Create a class that inherits from the `BaseAlerter` and implement the `post()` and `ask()` methods.

    ```python
    import logging
    from typing import Optional

    from zenml.alerter import BaseAlerter, BaseAlerterStepParameters


    class MyAlerter(BaseAlerter):
        """My alerter class."""

        def post(
            self, message: str, params: Optional[BaseAlerterStepParameters]
        ) -> bool:
            """Post a message to a chat service."""
            try:
                # Implement your chat service posting logic here
                # e.g., send HTTP request to chat API
                logging.info(f"Posting message: {message}")
                return True
            except Exception as e:
                logging.error(f"Failed to post message: {e}")
                return False

        def ask(
            self, question: str, params: Optional[BaseAlerterStepParameters]
        ) -> bool:
            """Post a message to a chat service and wait for approval."""
            try:
                # First, post the question
                if not self.post(question, params):
                    return False
                    
                # Define default approval/disapproval options
                approve_options = ["approve", "yes", "ok", "LGTM"]
                disapprove_options = ["reject", "no", "cancel", "stop"]
                
                # Check if custom options are provided in params
                if params and hasattr(params, 'approve_msg_options'):
                    approve_options = params.approve_msg_options
                if params and hasattr(params, 'disapprove_msg_options'):
                    disapprove_options = params.disapprove_msg_options
                
                # Wait for response (implement your chat service polling logic)
                # This is a simplified example - you'd implement actual polling
                response = self._wait_for_user_response()
                
                if response.lower() in [opt.lower() for opt in approve_options]:
                    return True
                elif response.lower() in [opt.lower() for opt in disapprove_options]:
                    return False
                else:
                    # Invalid response or timeout
                    return False
                    
            except Exception as e:
                print(f"Failed to get approval: {e}")
                return False
                
        def _wait_for_user_response(self) -> str:
            """Wait for user response - implement based on your chat service."""
            # This is where you'd implement the actual waiting logic
            # e.g., polling your chat service API for new messages
            return "approve"  # Placeholder
    ```
2.  If you need to configure your custom alerter, you can also implement a config object.

    ```python
    from zenml.alerter.base_alerter import BaseAlerterConfig


    class MyAlerterConfig(BaseAlerterConfig):
        my_param: str 
    ```

3.  Optionally, you can create custom parameter classes to support configurable approval/disapproval keywords:

    ```python
    from typing import List, Optional
    from zenml.alerter.base_alerter import BaseAlerterStepParameters


    class MyAlerterParameters(BaseAlerterStepParameters):
        """Custom parameters for MyAlerter."""
        
        # Custom approval/disapproval message options
        approve_msg_options: Optional[List[str]] = None
        disapprove_msg_options: Optional[List[str]] = None
        
        # Any other custom parameters for your alerter
        custom_channel: Optional[str] = None
    ```
4.  Finally, you can bring the implementation and the configuration together in a new flavor object.

    ```python
    from typing import Type, TYPE_CHECKING

    from zenml.alerter import BaseAlerterFlavor

    if TYPE_CHECKING:
        from zenml.stack import StackComponent, StackComponentConfig


    class MyAlerterFlavor(BaseAlerterFlavor):
        @property
        def name(self) -> str:
            return "my_alerter"

        @property
        def config_class(self) -> Type[StackComponentConfig]:
            from my_alerter_config import MyAlerterConfig

            return MyAlerterConfig

        @property
        def implementation_class(self) -> Type[StackComponent]:
            from my_alerter import MyAlerter

            return MyAlerter

    ```

Once you are done with the implementation, you can register your new flavor through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml alerter flavor register <path.to.MyAlerterFlavor>
```

For example, if your flavor class `MyAlerterFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml alerter flavor register flavors.my_flavor.MyAlerterFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](https://docs.zenml.io/how-to/project-setup-and-management/setting-up-a-project-repository/set-up-repository) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new custom alerter flavor in the list of available alerter flavors:

```shell
zenml alerter flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these abstractions are coming into play in a ZenML workflow.

* The **MyAlerterFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **MyAlerterConfig** class is imported when someone tries to register/update a stack component with the `my_alerter` flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are inherently `pydantic` objects, you can also add your own custom validators here.
* The **MyAlerter** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `MyAlerterFlavor` and the `MyAlerterConfig` are implemented in a different module/path than the actual `MyAlerter`).
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
