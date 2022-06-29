#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""ZenML console implementation."""


from rich.console import Console
from rich.style import Style
from rich.theme import Theme

zenml_style_defaults = {
    "info": Style(color="cyan", dim=True),
    "warning": Style(color="yellow"),
    "danger": Style(color="red", bold=True),
    "title": Style(color="cyan", bold=True, underline=True),
    "error": Style(color="red"),
}

zenml_custom_theme = Theme(zenml_style_defaults)

console = Console(theme=zenml_custom_theme, markup=True)
error_console = Console(stderr=True, theme=zenml_custom_theme)
