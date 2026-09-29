"""Launch a real ZenML evaluation using a local orchestrator and Docker."""

import argparse

from config import EvaluationConfig
from pipeline import endless_terminals_evaluation

from zenml.client import Client


def main() -> None:
    """Parse explicit execution settings and start the pipeline.

    Raises:
        RuntimeError: The active stack cannot run host Docker tasks.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["fixture", "endpoint", "kubernetes"],
        default="fixture",
    )
    parser.add_argument(
        "--task-id", action="append", dest="task_ids", default=[]
    )
    for name in (
        "data-directory",
        "output-directory",
        "base-url",
        "cloud-config-path",
        "model-name",
        "model-revision",
        "baseline-artifact-id",
    ):
        parser.add_argument(f"--{name}")
    for name in ("max-actions", "max-tokens"):
        parser.add_argument(f"--{name}", type=int)
    for name in ("temperature", "command-timeout", "episode-timeout"):
        parser.add_argument(f"--{name}", type=float)
    values = {
        key: value
        for key, value in vars(parser.parse_args()).items()
        if value is not None
    }
    config = EvaluationConfig(**values).resolve_directories()
    if Client().active_stack.orchestrator.flavor != "local":
        raise RuntimeError(
            "Select a local-orchestrator stack: this example uses Docker on this host"
        )
    endless_terminals_evaluation(config)


if __name__ == "__main__":
    main()
