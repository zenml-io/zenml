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

from pipeline import software_factory

from zenml.client import Client
from zenml.sandboxes import ContainerizedSandboxSettings


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
        "--target-branch", required=True, help="The branch to work on."
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
        default=3,
        help="The maximum number of test and review fix iterations.",
    )
    parser.add_argument(
        "--sandbox-image",
        required=True,
        help="Container image for the sandbox sessions of this run.",
    )
    args = parser.parse_args()

    if args.issue_file:
        with open(args.issue_file) as f:
            issue = f.read()
    elif args.issue:
        issue = args.issue
    else:
        parser.error("One of --issue or --issue-file is required.")

    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        parser.error("The active stack has no sandbox component.")

    pipeline = software_factory.with_options(
        settings={
            f"sandbox:{sandbox.name}": ContainerizedSandboxSettings(
                image=args.sandbox_image
            )
        }
    )
    pipeline(
        repo=args.repo,
        issue=issue,
        target_branch=args.target_branch,
        base_branch=args.base_branch,
        test_command=args.test_command,
        max_fix_iterations=args.max_fix_iterations,
    )


if __name__ == "__main__":
    main()
