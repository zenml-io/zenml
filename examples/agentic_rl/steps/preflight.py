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
"""Sandbox preflight: validate the substrate before billing a GPU."""

from typing import Any, Dict

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

SCORER_PATH = "/opt/zenml-scorer/score_pipeline.py"


@step(enable_cache=False)
def preflight_sandbox(image: str) -> Dict[str, Any]:
    """Prove the rollout substrate works before the trainer launches.

    Training rewards run inside sandbox sessions on this exact image;
    a broken image or sandbox turns every reward into a silent zero
    and burns the GPU budget on garbage. One session, two checks —
    zenml imports and the scorer is present — catches that class of
    failure in seconds. Uncached on purpose: it validates the world,
    which a cache hit would skip.

    Args:
        image: The scorer image every task and training rollout pins.

    Returns:
        The preflight verdict.

    Raises:
        RuntimeError: If no sandbox is on the stack, the image cannot
            run, zenml does not import inside it, or the scorer is
            missing.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError(
            "No Sandbox component on the active stack — register one "
            "before training (zenml sandbox register ...)."
        )
    settings = sandbox.image_settings(image)
    with sandbox.create_session(
        settings=settings, destroy_on_exit=True
    ) as session:
        checks = {
            "zenml_imports": ["python", "-c", "import zenml"],
            "scorer_present": ["test", "-f", SCORER_PATH],
        }
        for name, command in checks.items():
            output = session.exec(command).collect()
            if output.exit_code != 0:
                raise RuntimeError(
                    f"Sandbox preflight failed at '{name}' on image "
                    f"'{image}' (exit {output.exit_code}): "
                    f"{(output.stderr or output.stdout)[-500:]}. Fix "
                    "the environment before spending GPU time."
                )
    verdict = {"passed": True, "image": image, "checks": list(checks)}
    logger.info("Sandbox preflight passed on image '%s'.", image)
    return verdict
