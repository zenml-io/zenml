"""ZenML Quickstart - Simple Pipeline Example.

This is the simplest possible ZenML example to get started.

Usage:
    python run.py
"""

from pipelines.simple_pipeline import simple_pipeline


def main() -> None:
    """Run the simple pipeline."""
    print("🚀 Running ZenML quickstart pipeline...")
    _ = simple_pipeline()


if __name__ == "__main__":
    main()
