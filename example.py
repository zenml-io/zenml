"""ZenML + Trackio + Hugging Face ecosystem example."""

import json
from pathlib import Path

import trackio
from datasets import (
    Dataset,
    load_dataset,
)
from transformers import pipeline as hf_pipeline

from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.trackio.flavors.trackio_experiment_tracker_flavor import (
    TrackioExperimentTrackerSettings,
)

# ---------------------------------------------------------
# Active experiment tracker
# ---------------------------------------------------------

experiment_tracker = (
    Client()
    .active_stack
    .experiment_tracker
)

# ---------------------------------------------------------
# Artifact directory
# ---------------------------------------------------------

ARTIFACT_DIR = Path(
    "./trackio_artifacts"
)

ARTIFACT_DIR.mkdir(
    exist_ok=True
)

# ---------------------------------------------------------
# Hugging Face integration targets
# ---------------------------------------------------------

# Input dataset consumed by pipeline
HF_INPUT_DATASET = (
    "dair-ai/emotion"
)

# Output dataset containing
# Trackio inference logs/results
HF_OUTPUT_DATASET_REPO = (
    "AINovice2005/"
    "trackio-sentiment-results-v2"
)

# Trackio dashboard Space
HF_SPACE_ID = (
    "AINovice2005/"
    "trackio-sentiment-dashboard-v2"
)

HF_SPACE_URL = (
    "https://huggingface.co/spaces/"
    f"{HF_SPACE_ID}"
)

# ---------------------------------------------------------
# Trackio settings
# ---------------------------------------------------------

trackio_settings = (
    TrackioExperimentTrackerSettings(
        auto_sync=False,
        auto_freeze=False,
        resume="allow",
    )
)

# ---------------------------------------------------------
# Hugging Face sentiment pipeline
# ---------------------------------------------------------

classifier = hf_pipeline(
    task="sentiment-analysis",
    model=(
        "distilbert-base-uncased-"
        "finetuned-sst-2-english"
    ),
)

# ---------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------


@step
def load_input_dataset() -> Dataset:
    """Load dataset from Hugging Face Hub."""
    dataset = load_dataset(
        HF_INPUT_DATASET,
        split="train[:350]",
    )

    print(
        "\nLoaded input dataset:"
    )

    print(HF_INPUT_DATASET)

    return dataset


# ---------------------------------------------------------
# Sentiment inference
# ---------------------------------------------------------


@step(
    experiment_tracker=experiment_tracker.name,
    settings={
        "experiment_tracker": (
            trackio_settings
        ),
    },
)
def classify_sentiment(
    dataset: Dataset,
) -> Dataset:
    """Run sentiment inference."""
    results = []

    for row in dataset:
        prediction = classifier(
            row["text"]
        )[0]

        results.append(
            {
                "text": row["text"],
                "ground_truth": (
                    row["label"]
                ),
                "sentiment": (
                    prediction["label"]
                ),
                "score": float(
                    prediction["score"]
                ),
            }
        )

    result_dataset = (
        Dataset.from_list(
            results
        )
    )

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    positive_count = sum(
        1
        for row in results
        if row["sentiment"]
        == "POSITIVE"
    )

    negative_count = sum(
        1
        for row in results
        if row["sentiment"]
        == "NEGATIVE"
    )

    scores = [
        row["score"]
        for row in results
    ]

    metrics = {
        "num_samples": len(
            results
        ),
        "positive_count": (
            positive_count
        ),
        "negative_count": (
            negative_count
        ),
        "positive_ratio": (
            positive_count
            / len(results)
        ),
        "negative_ratio": (
            negative_count
            / len(results)
        ),
        "average_confidence": (
            sum(scores)
            / len(scores)
        ),
        "min_confidence": min(
            scores
        ),
        "max_confidence": max(
            scores
        ),
    }

    # -----------------------------------------------------
    # Trackio logging
    # -----------------------------------------------------

    trackio.log(metrics)

    trackio.log(
        {
            "model": (
                "distilbert-base-"
                "uncased-finetuned-"
                "sst-2-english"
            ),
            "hf_input_dataset": (
                HF_INPUT_DATASET
            ),
            "sample_predictions": (
                results[:10]
            ),
        }
    )

    # -----------------------------------------------------
    # Save local artifacts
    # -----------------------------------------------------

    predictions_path = (
        ARTIFACT_DIR
        / "predictions.json"
    )

    with open(
        predictions_path,
        "w",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    trackio.save(
        str(predictions_path)
    )

    metrics_path = (
        ARTIFACT_DIR
        / "metrics.json"
    )

    with open(
        metrics_path,
        "w",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
        )

    trackio.save(
        str(metrics_path)
    )

    # -----------------------------------------------------
    # Publish output dataset
    # -----------------------------------------------------

    result_dataset.push_to_hub(
        HF_OUTPUT_DATASET_REPO,
        private=False,
    )

    print(
        "\nOutput dataset pushed:"
    )

    print(
        HF_OUTPUT_DATASET_REPO
    )

    # -----------------------------------------------------
    # Publish Space metadata
    # -----------------------------------------------------

    trackio.log(
        {
            "space_status": (
                "published"
            ),
            "space_url": (
                HF_SPACE_URL
            ),
        }
    )

    trackio.sync(project=experiment_tracker.config.project_name)
    print(
        "\nHF Space dashboard:"
    )

    print(HF_SPACE_URL)

    return result_dataset


# ---------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------


@pipeline(
    enable_cache=False,
    enable_pipeline_logs=False,
)
def sentiment_analysis_pipeline():
    """HF + Trackio pipeline."""
    dataset = load_input_dataset()

    classify_sentiment(dataset)


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    print(
        "\nRunning ZenML + "
        "Trackio + HF pipeline...\n"
    )

    pipeline_settings = {
        "experiment_tracker": (
            TrackioExperimentTrackerSettings(
                auto_sync=True,
                auto_freeze=False,
                resume="allow",
            )
        )
    }

    sentiment_analysis_pipeline.with_options(
        settings=pipeline_settings,
    )()

    print(
        "\nPipeline completed successfully."
    )