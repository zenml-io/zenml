#!/usr/bin/env python3
"""
Quick launcher for FiftyOne dashboard to view computer vision results.

This script helps you easily access the FiftyOne dashboard to explore your
trained model's predictions vs ground truth annotations.
"""

import sys

import fiftyone as fo

from zenml.logger import get_logger

logger = get_logger(__name__)


def list_available_datasets():
    """List all available FiftyOne datasets."""
    datasets = fo.list_datasets()
    if not datasets:
        logger.info("No FiftyOne datasets found.")
        return []

    logger.info("Available FiftyOne datasets:")
    for i, name in enumerate(datasets, 1):
        dataset = fo.load_dataset(name)
        sample_count = len(dataset)
        has_predictions = "predictions" in dataset.get_field_schema().keys()
        pred_status = (
            "✅ Has predictions" if has_predictions else "❌ No predictions"
        )
        logger.info(f"{i}. {name} ({sample_count} samples) - {pred_status}")

    return datasets


def launch_dataset(dataset_name: str, port: int = 5151):
    """Launch FiftyOne app with specific dataset."""
    try:
        dataset = fo.load_dataset(dataset_name)
        logger.info(f"Loading dataset: {dataset_name}")
        logger.info(f"Samples: {len(dataset)}")

        # Check if it has predictions
        has_predictions = "predictions" in dataset.get_field_schema().keys()
        if has_predictions:
            logger.info(
                "✅ Dataset has predictions - you can compare with ground truth!"
            )
        else:
            logger.info("❌ Dataset has no predictions - run training first")

        logger.info("Launching FiftyOne App...")
        logger.info(f"🌐 Opening browser to http://localhost:{port}")

        session = fo.launch_app(dataset, port=port)

        logger.info("\n🎯 FiftyOne Dashboard Controls:")
        logger.info(
            "• Use filters to explore specific classes or confidence ranges"
        )
        logger.info("• Click on samples to see detailed annotations")
        logger.info("• Compare ground_truth vs predictions fields")
        logger.info("• Export interesting samples for further analysis")
        logger.info("\nPress Ctrl+C to stop the FiftyOne app")

        # Keep the session alive
        session.wait()

    except KeyboardInterrupt:
        logger.info("\nStopping FiftyOne app...")
    except Exception as e:
        logger.error(f"Error launching dataset: {e}")


def main():
    """Main function to handle command line usage."""
    print("🔍 FiftyOne Dashboard Launcher")
    print("=" * 40)

    port = 5151  # Default port
    dataset_name = None

    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
                i += 2
            except ValueError:
                logger.error(f"Invalid port number: {args[i + 1]}")
                return
        elif not dataset_name:
            dataset_name = args[i]
            i += 1
        else:
            logger.error(f"Unknown argument: {args[i]}")
            return

    if dataset_name:
        launch_dataset(dataset_name, port)
    else:
        datasets = list_available_datasets()
        if not datasets:
            logger.info("Run training first to generate datasets:")
            logger.info("python run.py --train --samples 10 --epochs 1")
            return

        logger.info("\nUsage:")
        logger.info("python launch_fiftyone.py <dataset_name> [--port <port>]")
        logger.info("\nExamples:")
        logger.info(f"python launch_fiftyone.py {datasets[0]}")
        logger.info(f"python launch_fiftyone.py {datasets[0]} --port 8080")


if __name__ == "__main__":
    main()
