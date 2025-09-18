"""ZenML steps for prompt optimization example.

Simple, focused steps that demonstrate ZenML's core capabilities:
- Data ingestion 
- AI-powered analysis
- Prompt optimization and tagging
"""

from .eda_agent import run_eda_agent
from .ingest import ingest_data
from .prompt_optimization import compare_prompts_and_tag_best, get_optimized_prompt

__all__ = [
    "ingest_data",
    "run_eda_agent", 
    "compare_prompts_and_tag_best",
    "get_optimized_prompt",
]