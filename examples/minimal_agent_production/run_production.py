"""Script to run the document analysis production pipeline.

This script executes the production document analysis pipeline
with sample input data for testing and demonstration purposes.
"""

from __future__ import annotations

from pipelines import document_analysis_pipeline

if __name__ == "__main__":
    # Sample document analysis
    document_analysis_pipeline.with_options(enable_cache=False)(
        filename="sample_document.txt",
        content="This is a sample document for analysis. It contains various types of content that will be processed through our document analysis pipeline. The system will extract key information, analyze sentiment, and generate a comprehensive report.",
        document_type="text",
        analysis_type="full",
    )
