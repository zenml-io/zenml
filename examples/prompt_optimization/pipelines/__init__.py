"""ZenML pipelines for prompt optimization example.

This module contains pipeline definitions:

- prompt_optimization_pipeline.py: Test prompts and tag the best one
- production_eda_pipeline.py: Use optimized prompt for EDA analysis  
"""

from .production_eda_pipeline import production_eda_pipeline
from .prompt_optimization_pipeline import prompt_optimization_pipeline

__all__ = [
    "prompt_optimization_pipeline",
    "production_eda_pipeline", 
]