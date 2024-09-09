#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utilities for CLI output."""

from typing import List

from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import Heading, Markdown
from rich.text import Text

zenml_cli_welcome_message = Markdown(
    """
# ⛩  Welcome to ZenML!
"""
)

zenml_cli_email_prompt = Markdown(
    """
Here at ZenML we are working hard to produce the best
possible MLOps framework. In order to solve real-world problems
we want to ask you, the user, for feedback and ideas. If
you are interested in helping us shape the world of MLOps
please leave your email below (or leave blank to skip). We will
only use this for the purpose of reaching out to you for a
user interview and to better understand usage.
"""
)

zenml_cli_privacy_message = Markdown(
    """
## 🔒 Privacy Policy at ZenML!

As an open-source project we rely on usage statistics to inform our decisions
about what features to build. The statistics do not contain any of your code,
data or personal information. All we see on our end is metadata like operating
system, stack component flavors and that events like pipeline runs were
triggered.

If you wish to opt out, feel free to run the following command:
```bash
zenml analytics opt-out
```
"""
)

zenml_cli_thank_you_message = Markdown(
    """
🙏  Thank you!
"""
)


def zenml_go_notebook_tutorial_message(ipynb_files: List[str]) -> Markdown:
    """Outputs a message to the user about the `zenml go` tutorial.

    Args:
        ipynb_files: A list of IPython Notebook files.

    Returns:
        A Markdown object.
    """
    ipynb_files = [f"- {fi} \n" for fi in ipynb_files]
    return Markdown(
        f"""
## 🧑‍🏫 Get started with ZenML

The ZenML tutorial repository was cloned to your current working directory.
Within the repository you can get started on one of these notebooks:
{''.join(ipynb_files)}
Next we will start a Jupyter notebook server. Feel free to try your hand at our
tutorial notebooks. If your browser does not open automatically click one of the
links below.\n

"""
    )


class OldSchoolMarkdownHeading(Heading):
    """A traditional markdown heading."""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> Generator[RenderResult, None, None]:
        """Render the heading to the console.

        Args:
            console: The console to render to.
            options: The console options.

        Yields:
            RenderResult: The rendered heading.
        """
        text = self.text
        text.justify = "left"
        if self.tag == "h1":
            # Underline and bold h1s
            yield Text("", style="bold")
            yield text
            yield "=" * len(text)
        else:
            if self.tag == "h2":
                # Just underline h2s
                yield Text("", style="underline")
            else:
                # Just bold everything else
                yield Text("", style="bold")
            yield text
