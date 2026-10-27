#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""CLI group that gathers all commands deleting unused data."""

from zenml.cli.artifact import prune_artifacts
from zenml.cli.cli import TagGroup, cli
from zenml.cli.pipeline import prune_pipeline_snapshots
from zenml.enums import CliCategories


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def prune() -> None:
    """Commands for deleting unused data."""


# The commands stay registered under their resource groups as well, so both
# `zenml prune artifacts` and `zenml artifact prune` work.
prune.add_command(prune_artifacts, name="artifacts")
prune.add_command(prune_pipeline_snapshots, name="snapshots")
