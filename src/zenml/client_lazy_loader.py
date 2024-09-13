#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Lazy loading functionality for Client methods."""

import contextlib
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel

if TYPE_CHECKING:
    from zenml.client import Client


class _CallStep(BaseModel):
    attribute_name: Optional[str] = None
    is_call: Optional[bool] = False
    call_args: Optional[List[Any]] = []
    call_kwargs: Optional[Dict[str, Any]] = {}
    selector: Optional[Any] = None


class ClientLazyLoader(BaseModel):
    """Lazy loader for Client methods."""

    method_name: str
    call_chain: List[_CallStep] = []
    exclude_next_call: bool = False

    def __getattr__(self, name: str) -> "ClientLazyLoader":
        """Get attribute not defined in ClientLazyLoader.

        Args:
            name: Name of the attribute to get.

        Returns:
            self
        """
        self_ = ClientLazyLoader(
            method_name=self.method_name, call_chain=self.call_chain.copy()
        )
        # workaround to protect from infinitely looping over in deepcopy called in invocations
        if name != "__deepcopy__":
            self_.call_chain.append(_CallStep(attribute_name=name))
        else:
            self_.exclude_next_call = True
        return self_

    def __call__(self, *args: Any, **kwargs: Any) -> "ClientLazyLoader":
        """Call mocked attribute.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            self
        """
        # workaround to protect from infinitely looping over in deepcopy called in invocations
        if not self.exclude_next_call:
            self.call_chain.append(
                _CallStep(is_call=True, call_args=args, call_kwargs=kwargs)
            )
        self.exclude_next_call = False
        return self

    def __getitem__(self, item: Any) -> "ClientLazyLoader":
        """Get item from mocked attribute.

        Args:
            item: Item to get.

        Returns:
            self
        """
        self.call_chain.append(_CallStep(selector=item))
        return self

    def evaluate(self) -> Any:
        """Evaluate lazy loaded Client method.

        Returns:
            Evaluated lazy loader chain of calls.
        """
        from zenml.client import Client

        def _iterate_over_lazy_chain(
            self: "ClientLazyLoader", self_: Any, call_chain_: List[_CallStep]
        ) -> Any:
            next_step = call_chain_.pop(0)
            try:
                if next_step.is_call:
                    self_ = self_(
                        *next_step.call_args, **next_step.call_kwargs
                    )
                elif next_step.selector:
                    self_ = self_[next_step.selector]
                elif next_step.attribute_name:
                    self_ = getattr(self_, next_step.attribute_name)
                else:
                    raise ValueError(
                        "Invalid call chain. Reach out to the ZenML team."
                    )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to evaluate lazy load chain `{self.method_name}` "
                    f"+ `{self.call_chain}`. Reach out to the ZenML team via "
                    "Slack or GitHub to check further."
                ) from e
            return self_

        self_ = getattr(Client(), self.method_name)
        call_chain_ = self.call_chain.copy()
        while call_chain_:
            self_ = _iterate_over_lazy_chain(self, self_, call_chain_)
        return self_


def client_lazy_loader(
    method_name: str, *args: Any, **kwargs: Any
) -> Optional[ClientLazyLoader]:
    """Lazy loader for Client methods helper.

    Usage:
    ```
    def get_something(self, arg1: Any)->SomeResponse:
        if cll:=client_lazy_loader("get_something", arg1):
            return cll # type: ignore[return-value]
        return SomeResponse()
    ```

    Args:
        method_name: The name of the method to be called.
        *args: The arguments to be passed to the method.
        **kwargs: The keyword arguments to be passed to the method.

    Returns:
        The result of the method call.
    """
    from zenml import get_pipeline_context

    try:
        get_pipeline_context()
        cll = ClientLazyLoader(
            method_name=method_name,
        )
        return cll(*args, **kwargs)
    except RuntimeError:
        return None


def evaluate_all_lazy_load_args_in_client_methods(
    cls: Type["Client"],
) -> Type["Client"]:
    """Class wrapper to evaluate lazy loader arguments of all methods.

    Args:
        cls: The class to wrap.

    Returns:
        Wrapped class.
    """
    import inspect

    def _evaluate_args(func: Callable[..., Any]) -> Any:
        def _inner(*args: Any, **kwargs: Any) -> Any:
            is_instance_method = "self" in inspect.getfullargspec(func).args

            args_ = list(args)
            if not is_instance_method:
                from zenml.client import Client

                if args and isinstance(args[0], Client):
                    args_ = list(args[1:])

            for i in range(len(args_)):
                if isinstance(args_[i], dict):
                    with contextlib.suppress(ValueError):
                        args_[i] = ClientLazyLoader(**args_[i]).evaluate()
                elif isinstance(args_[i], ClientLazyLoader):
                    args_[i] = args_[i].evaluate()

            for k, v in kwargs.items():
                if isinstance(v, dict):
                    with contextlib.suppress(ValueError):
                        kwargs[k] = ClientLazyLoader(**v).evaluate()

            return func(*args_, **kwargs)

        return _inner

    def _decorate() -> Type["Client"]:
        for name, fn in inspect.getmembers(cls, inspect.isfunction):
            setattr(cls, name, _evaluate_args(fn))
        return cls

    return _decorate()
