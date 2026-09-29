"""Launch the bounded native ZenML terminal-agent training pipeline."""

import argparse
import json
from pathlib import Path

from config import TrainingConfig
from training import endless_terminals_training

from zenml.client import Client


def main() -> None:
    """Validate an explicit JSON configuration and launch the training run.

    Raises:
        RuntimeError: The selected stack does not use the local orchestrator.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    config = TrainingConfig(
        **json.loads(parser.parse_args().config.read_text())
    ).resolve_directories()
    if Client().active_stack.orchestrator.flavor != "local":
        raise RuntimeError(
            "Training requires a local orchestrator for host Docker tasks"
        )
    endless_terminals_training(config)


if __name__ == "__main__":
    main()
