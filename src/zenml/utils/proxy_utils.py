#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Proxy design pattern utils."""

from abc import ABC
from functools import wraps
from typing import Any, Callable, Type, TypeVar, cast

C = TypeVar("C", bound=Type[ABC])
F = TypeVar("F", bound=Callable[..., Any])


def make_proxy_class(interface: Type[ABC], attribute: str) -> Callable[[C], C]:
    """Proxy class decorator.

    Use this decorator to transform the decorated class into a proxy that
    forwards all calls defined in the `interface` interface to the `attribute`
    class attribute that implements the same interface.

    This class is useful in cases where you need to have a base class that acts
    as a proxy or facade for one or more other classes. Both the decorated class
    and the class attribute must inherit from the same ABC interface for this to
    work. Only regular methods are supported, not class methods or attributes.

    Example: Let's say you have an interface called `BodyBuilder`, a base class
    called `FatBob` and another class called `BigJim`. `BigJim` implements the
    `BodyBuilder` interface, but `FatBob` does not. And let's say you want
    `FatBob` to look as if it implements the `BodyBuilder` interface, but in
    fact it just forwards all calls to `BigJim`. You could do this:

    ```python
    from abc import ABC, abstractmethod

    class BodyBuilder(ABC):

        @abstractmethod
        def build_body(self):
            pass

    class BigJim(BodyBuilder):

        def build_body(self):
            print("Looks fit!")

    class FatBob(BodyBuilder)

        def __init__(self):
            self.big_jim = BigJim()

        def build_body(self):
            self.big_jim.build_body()

    fat_bob = FatBob()
    fat_bob.build_body()
    ```

    But this leads to a lot of boilerplate code with bigger interfaces and
    makes everything harder to maintain. This is where the proxy class
    decorator comes in handy. Here's how to use it:

    ```python
    from zenml.utils.proxy_utils import make_proxy_class
    from typing import Optional

    @make_proxy_class(BodyBuilder, "big_jim")
    class FatBob(BodyBuilder)
        big_jim: Optional[BodyBuilder] = None

        def __init__(self):
            self.big_jim = BigJim()

    fat_bob = FatBob()
    fat_bob.build_body()
    ```

    This is the same as implementing FatBob to call BigJim explicitly, but it
    has the advantage that you don't need to write a lot of boilerplate code
    of modify the FatBob class every time you change something in the
    BodyBuilder interface.

    This proxy decorator also allows to extend classes dynamically at runtime:
    if the `attribute` class attribute is set to None, the proxy class
    will assume that the interface is not implemented by the class and will
    raise a NotImplementedError:

    ```python
    @make_proxy_class(BodyBuilder, "big_jim")
    class FatBob(BodyBuilder)
        big_jim: Optional[BodyBuilder] = None

        def __init__(self):
            self.big_jim = None

    fat_bob = FatBob()

    # Raises NotImplementedError, class not extended yet:
    fat_bob.build_body()

    fat_bob.big_jim = BigJim()
    # Now it works:
    fat_bob.build_body()
    ```

    Args:
        interface: The interface to implement.
        attribute: The attribute of the base class to forward calls to.

    Returns:
        The proxy class.
    """

    def make_proxy_method(cls: C, _method: F) -> F:
        """Proxy method decorator.

        Used to transform a method into a proxy that forwards all calls to the
        given class attribute.

        Args:
            cls: The class to use as the base.
            _method: The method to replace.

        Returns:
            The proxy method.
        """

        @wraps(_method)
        def proxy_method(*args: Any, **kw: Any) -> Any:
            """Proxy method.

            Args:
                *args: The arguments to pass to the method.
                **kw: The keyword arguments to pass to the method.

            Returns:
                The return value of the proxied method.

            Raises:
                TypeError: If the class does not have the attribute specified
                    in the decorator or if the attribute does not implement
                    the specified interface.
                NotImplementedError: If the attribute specified in the
                    decorator is None, i.e. the interface is not implemented.
            """
            self = args[0]
            if not hasattr(self, attribute):
                raise TypeError(
                    f"Class '{cls.__name__}' does not have a '{attribute}' "
                    f"as specified in the 'make_proxy_class' decorator."
                )
            proxied_obj = getattr(self, attribute)
            if proxied_obj is None:
                raise NotImplementedError(
                    f"This '{cls.__name__}' instance does not implement the "
                    f"'{interface.__name__}' interface."
                )
            if not isinstance(proxied_obj, interface):
                raise TypeError(
                    f"Interface '{interface.__name__}' must be implemented by "
                    f"the '{cls.__name__}' '{attribute}' attribute."
                )
            proxied_method = getattr(proxied_obj, _method.__name__)
            return proxied_method(*args[1:], **kw)

        return cast(F, proxy_method)

    def _inner_decorator(_cls: C) -> C:
        """Inner proxy class decorator.

        Args:
            _cls: The class to decorate.

        Returns:
            The decorated class.

        Raises:
            TypeError: If the decorated class does not implement the specified
                interface.
        """
        if not issubclass(_cls, interface):
            raise TypeError(
                f"Interface '{interface.__name__}' must be implemented by "
                f"the '{_cls.__name__}' class."
            )

        for method_name in interface.__abstractmethods__:
            original_method = getattr(_cls, method_name)
            method_proxy = make_proxy_method(_cls, original_method)
            # Make sure the proxy method is not considered abstract.
            method_proxy.__isabstractmethod__ = False
            setattr(_cls, method_name, method_proxy)

        # Remove the abstract methods in the interface from the decorated class.
        _cls.__abstractmethods__ = frozenset(
            method_name
            for method_name in _cls.__abstractmethods__
            if method_name not in interface.__abstractmethods__
        )

        return cast(C, _cls)

    return _inner_decorator
