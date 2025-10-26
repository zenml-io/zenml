"""ZenML Quickstart - Simple Pipeline Example.

This is the simplest possible ZenML example to get started.

Usage:
    python run.py
"""

from pipelines.simple_pipeline import simple_pipeline


def main() -> None:
    """Run the simple pipeline."""
    print("🚀 Running ZenML quickstart pipeline...")
    result = simple_pipeline()
    print(f"✅ Pipeline completed! Result: {result}")


if __name__ == "__main__":
    main()
