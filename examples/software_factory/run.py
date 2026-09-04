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
"""CLI entrypoint for the software factory pipeline."""

import argparse

from factory_utils import active_sandbox
from pipeline import software_factory

from zenml.sandboxes import ContainerizedSandboxSettings
from zenml.utils.settings_utils import get_stack_component_name_setting_key


def main() -> None:
    """Parse arguments and run the software factory pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo", required=True, help="Repository, owner/name."
    )
    parser.add_argument("--issue", help="The issue description text.")
    parser.add_argument(
        "--issue-file", help="Path to a file containing the issue description."
    )
    parser.add_argument(
        "--target-branch",
        help="The branch to work on. Derived from the issue title if not set.",
    )
    parser.add_argument(
        "--base-branch",
        help="The branch to create the work branch from and to open the "
        "pull request against. Defaults to the repository's default branch.",
    )
    parser.add_argument(
        "--test-command",
        help="Shell command that runs the tests in the checkout. Tests are "
        "skipped if not set.",
    )
    parser.add_argument(
        "--max-fix-iterations",
        type=int,
        default=2,
        help="The maximum number of fix rounds. Zero means test and review "
        "only.",
    )
    parser.add_argument(
        "--sandbox-image",
        required=True,
        help="Container image for the sandbox sessions of this run.",
    )
    parser.add_argument(
        "--agent-model",
        default="sonnet",
        help="Model alias or id for the agent, for example sonnet or opus.",
    )
    parser.add_argument(
        "--gate-timeout",
        type=int,
        default=600,
        help="Seconds each approval gate waits before the run is paused.",
    )
    args = parser.parse_args()

    if args.issue_file:
        with open(args.issue_file) as f:
            issue = f.read()
    elif args.issue:
        issue = args.issue
    else:
        parser.error("One of --issue or --issue-file is required.")

    sandbox = active_sandbox()
    pipeline = software_factory.with_options(
        settings={
            get_stack_component_name_setting_key(
                sandbox
            ): ContainerizedSandboxSettings(image=args.sandbox_image)
        }
    )
    pipeline(
        repo=args.repo,
        issue=issue,
        target_branch=args.target_branch,
        base_branch=args.base_branch,
        test_command=args.test_command,
        max_fix_iterations=args.max_fix_iterations,
        agent_model=args.agent_model,
        gate_timeout=args.gate_timeout,
    )


if __name__ == "__main__":
    main()
