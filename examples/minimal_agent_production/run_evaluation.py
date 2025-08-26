"""Script to run the document analysis evaluation pipeline.

This script executes the evaluation pipeline to assess the quality
of document analysis outputs and generate evaluation reports.
"""

from __future__ import annotations

from pipelines import evaluation_pipeline

if __name__ == "__main__":
    evaluation_pipeline(max_items=125)
