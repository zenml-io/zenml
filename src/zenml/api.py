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
"""Public Python API of ZenML.

Everything defined/imported here should be highly import-optimized so we don't
slow down the CLI.
"""


def show() -> None:
    """Show the ZenML dashboard."""
    from zenml.utils.dashboard_utils import show_dashboard
    from zenml.zen_server.utils import get_server_url

    show_dashboard(get_server_url())
