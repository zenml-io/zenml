#!/usr/bin/env python3
"""
Quick launcher for FiftyOne dashboard to view computer vision results.

This script helps you easily access the FiftyOne dashboard to explore your
trained model's predictions vs ground truth annotations.
"""

import sys

from annotators import FiftyOneAnnotator

from zenml.logger import get_logger

logger = get_logger(__name__)


def list_available_datasets():
    """List all available FiftyOne datasets."""
    # Use FiftyOne annotator for dataset management
    annotator = FiftyOneAnnotator()
    datasets = annotator.get_dataset_names()

    if not datasets:
        logger.info("No FiftyOne datasets found.")
        return []

    logger.info("Available FiftyOne datasets:")
    for i, name in enumerate(datasets, 1):
        try:
            labeled_count, unlabeled_count = annotator.get_dataset_stats(name)
            total_samples = labeled_count + unlabeled_count
            pred_status = (
                f"✅ Has predictions ({labeled_count} labeled)"
                if labeled_count > 0
                else "❌ No predictions"
            )
            logger.info(
                f"{i}. {name} ({total_samples} samples) - {pred_status}"
            )
            # Compact prediction version summary (if available)
            versions = annotator.describe_prediction_versions(name)
            if versions:
                latest = next(
                    (v for v in versions if v.get("is_latest")), None
                )
                latest_field = (
                    latest.get("field") if latest else versions[0].get("field")
                )
                logger.info(
                    f"   ↳ {len(versions)} prediction versions available; latest: {latest_field}"
                )
        except Exception as e:
            logger.warning(f"Could not get stats for dataset {name}: {e}")

    return datasets


def launch_dataset(dataset_name: str, port: int = 5151):
    """Launch FiftyOne app with specific dataset."""
    try:
        # Use FiftyOne annotator for launching
        annotator = FiftyOneAnnotator()

        # Get dataset stats
        labeled_count, unlabeled_count = annotator.get_dataset_stats(
            dataset_name
        )
        total_samples = labeled_count + unlabeled_count

        logger.info(f"Loading dataset: {dataset_name}")
        logger.info(f"Samples: {total_samples}")

        # Check if it has predictions
        if labeled_count > 0:
            logger.info(
                f"✅ Dataset has predictions ({labeled_count} labeled) - you can compare with ground truth!"
            )
        else:
            logger.info("❌ Dataset has no predictions - run training first")

        # Detailed prediction version list (if available)
        versions = annotator.describe_prediction_versions(dataset_name)
        if versions:
            logger.info("Prediction versions:")
            for v in versions:
                field = v.get("field")
                created = v.get("created_at")
                is_latest = v.get("is_latest")
                latest_marker = " (latest)" if is_latest else ""
                if created:
                    logger.info(
                        f"  • {field}{latest_marker} - created_at: {created}"
                    )
                else:
                    logger.info(f"  • {field}{latest_marker}")
            logger.info(f"Total versions: {len(versions)}")
            latest = next((v for v in versions if v.get("is_latest")), None)
            latest_field = (
                latest.get("field") if latest else versions[0].get("field")
            )
            logger.info(f"Using latest predictions field: '{latest_field}'")
            logger.info(
                "Tip: Use the FiftyOne field selector (left sidebar) to switch between prediction versions."
            )
        else:
            logger.info("No prediction versions found for this dataset yet.")

        logger.info("Launching FiftyOne App...")
        logger.info(f"🌐 Opening browser to http://localhost:{port}")

        # Launch using annotator
        session = annotator.launch(dataset_name=dataset_name, port=port)

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
