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
"""Internal BaseStep subclass used by the step decorator."""

from typing import Any, Optional

from zenml.config.source import Source
from zenml.steps import BaseStep, step


def remove_decorator_from_source_code(
    source_code: str, decorator_name: str
) -> str:
    """Remove a decorator from the source code of a function.

    Args:
        source_code: The source code of the function.
        decorator_name: The name of the decorator.

    Returns:
        The source code of the function without the decorator.
    """
    import ast

    # Remove potential indentation from the source code
    source_code_lines = source_code.split("\n")
    if source_code_lines:
        first_line = source_code_lines[0]
        leading_spaces = len(first_line) - len(first_line.lstrip())
        source_code_lines = [
            line[leading_spaces:] if len(line) >= leading_spaces else line
            for line in source_code_lines
        ]

    module = ast.parse("\n".join(source_code_lines))
    if not module.body or not isinstance(module.body[0], ast.FunctionDef):
        return source_code

    function_def = module.body[0]
    if not function_def.decorator_list:
        return source_code

    for decorator in function_def.decorator_list:
        lineno = None
        end_lineno = None

        if isinstance(decorator, ast.Call) and isinstance(
            decorator.func, ast.Name
        ):
            if decorator.func.id == decorator_name:
                lineno = decorator.lineno
                end_lineno = decorator.end_lineno
        elif isinstance(decorator, ast.Name):
            if decorator.id == decorator_name:
                lineno = decorator.lineno
                end_lineno = decorator.end_lineno
        else:
            continue

        if lineno is not None and end_lineno is not None:
            # The line numbers are 1-indexed, so we need to
            # subtract 1
            source_code_lines = (
                source_code_lines[: lineno - 1]
                + source_code_lines[end_lineno:]
            )
            source_code = "\n".join(source_code_lines)
            break

    return source_code


class _DecoratedStep(BaseStep):
    """Internal BaseStep subclass used by the step decorator."""

    def _get_step_decorator_name(self) -> Optional[str]:
        """The name of the step decorator.

        Returns:
            The name of the step decorator.
        """
        decorator_names = [
            key
            for key, value in self.entrypoint.__globals__.items()
            if value is step
        ]
        if not decorator_names:
            return None

        return decorator_names[0]

    @property
    def source_code_cache_value(self) -> str:
        """The source code cache value of this step.

        Returns:
            The source code cache value of this step.
        """
        try:
            if decorator_name := self._get_step_decorator_name():
                return remove_decorator_from_source_code(
                    source_code=self.source_code,
                    decorator_name=decorator_name,
                )
        except Exception:
            pass

        return super().source_code_cache_value

    @property
    def source_object(self) -> Any:
        """The source object of this step.

        Returns:
            The source object of this step.
        """
        return self.entrypoint

    def resolve(self) -> "Source":
        """Resolves the step.

        Returns:
            The step source.
        """
        from zenml.utils import source_utils

        return source_utils.resolve(self.entrypoint, skip_validation=True)
