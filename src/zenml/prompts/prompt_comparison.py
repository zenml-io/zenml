#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Prompt comparison utilities for analyzing and comparing prompts."""

import difflib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from zenml.prompts.prompt import Prompt


class PromptDiff(BaseModel):
    """Represents differences between two prompts."""

    field: str = Field(..., description="Field name that differs")
    prompt1_value: Any = Field(..., description="Value in first prompt")
    prompt2_value: Any = Field(..., description="Value in second prompt")
    diff_type: str = Field(
        ..., description="Type of difference: 'added', 'removed', 'modified'"
    )


class TemplateComparison(BaseModel):
    """Detailed comparison of prompt templates."""

    similarity_score: float = Field(
        ..., description="Similarity score between 0.0 and 1.0"
    )
    common_variables: List[str] = Field(
        default_factory=list, description="Variables present in both templates"
    )
    unique_to_first: List[str] = Field(
        default_factory=list, description="Variables only in first template"
    )
    unique_to_second: List[str] = Field(
        default_factory=list, description="Variables only in second template"
    )
    diff_lines: List[str] = Field(
        default_factory=list, description="Line-by-line diff"
    )
    character_diff: List[Tuple[str, str]] = Field(
        default_factory=list, description="Character-level differences"
    )


class PromptComparison(BaseModel):
    """Comprehensive comparison between prompts."""

    prompt1_id: str = Field(..., description="ID of first prompt")
    prompt2_id: str = Field(..., description="ID of second prompt")

    # High-level comparison
    overall_similarity: float = Field(
        ..., description="Overall similarity score"
    )
    is_compatible: bool = Field(
        ..., description="Whether prompts are compatible for A/B testing"
    )

    # Field-by-field differences
    differences: List[PromptDiff] = Field(
        default_factory=list, description="List of differences between prompts"
    )

    # Template comparison
    template_comparison: TemplateComparison = Field(
        ..., description="Detailed template comparison"
    )

    # Performance comparison (if available)
    performance_comparison: Optional[Dict[str, Dict[str, float]]] = Field(
        default=None, description="Performance metrics comparison"
    )

    # Metadata
    compared_at: datetime = Field(
        default_factory=datetime.now,
        description="When comparison was performed",
    )
    comparison_version: str = Field(
        default="1.0", description="Version of comparison algorithm"
    )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the comparison."""
        return {
            "overall_similarity": self.overall_similarity,
            "is_compatible": self.is_compatible,
            "total_differences": len(self.differences),
            "template_similarity": self.template_comparison.similarity_score,
            "has_performance_data": self.performance_comparison is not None,
            "major_differences": [
                diff
                for diff in self.differences
                if diff.field
                in ["template", "task", "domain", "prompt_strategy"]
            ],
        }

    def get_recommendation(self) -> str:
        """Get a recommendation based on the comparison."""
        if self.overall_similarity > 0.9:
            return "Prompts are very similar. Consider consolidating."
        elif self.overall_similarity > 0.7:
            return "Prompts are similar. Good candidates for A/B testing."
        elif self.overall_similarity > 0.5:
            return "Prompts have moderate similarity. Review differences before comparing."
        else:
            return "Prompts are quite different. Ensure fair comparison conditions."


def compare_prompts(prompt1: Prompt, prompt2: Prompt) -> PromptComparison:
    """Compare two prompts comprehensively.

    Args:
        prompt1: First prompt to compare
        prompt2: Second prompt to compare

    Returns:
        PromptComparison object with detailed analysis
    """
    # Calculate differences
    differences = _calculate_differences(prompt1, prompt2)

    # Compare templates
    template_comparison = _compare_templates(
        prompt1.template, prompt2.template
    )

    # Calculate overall similarity
    overall_similarity = _calculate_overall_similarity(
        prompt1, prompt2, template_comparison
    )

    # Check compatibility
    is_compatible = _check_compatibility(prompt1, prompt2, differences)

    # Compare performance if available
    performance_comparison = _compare_performance(prompt1, prompt2)

    return PromptComparison(
        prompt1_id=prompt1.prompt_id or "unknown",
        prompt2_id=prompt2.prompt_id or "unknown",
        overall_similarity=overall_similarity,
        is_compatible=is_compatible,
        differences=differences,
        template_comparison=template_comparison,
        performance_comparison=performance_comparison,
    )


def _calculate_differences(
    prompt1: Prompt, prompt2: Prompt
) -> List[PromptDiff]:
    """Calculate field-by-field differences between prompts."""
    differences = []

    # Fields to compare
    fields_to_compare = [
        "template",
        "prompt_type",
        "task",
        "domain",
        "prompt_strategy",
        "instructions",
        "context_template",
        "model_config_params",
        "target_models",
        "description",
        "version",
        "tags",
        "variables",
        "examples",
        "min_tokens",
        "max_tokens",
        "expected_format",
        "language",
        "safety_checks",
    ]

    prompt1_dict = prompt1.to_dict()
    prompt2_dict = prompt2.to_dict()

    for field in fields_to_compare:
        value1 = prompt1_dict.get(field)
        value2 = prompt2_dict.get(field)

        if value1 != value2:
            # Determine diff type
            if value1 is None:
                diff_type = "added"
            elif value2 is None:
                diff_type = "removed"
            else:
                diff_type = "modified"

            differences.append(
                PromptDiff(
                    field=field,
                    prompt1_value=value1,
                    prompt2_value=value2,
                    diff_type=diff_type,
                )
            )

    return differences


def _compare_templates(template1: str, template2: str) -> TemplateComparison:
    """Compare prompt templates in detail."""
    import re

    # Extract variables
    pattern = r"\{([^}]+)\}"
    vars1 = set(re.findall(pattern, template1))
    vars2 = set(re.findall(pattern, template2))

    common_variables = list(vars1.intersection(vars2))
    unique_to_first = list(vars1 - vars2)
    unique_to_second = list(vars2 - vars1)

    # Calculate similarity using difflib
    similarity = difflib.SequenceMatcher(None, template1, template2).ratio()

    # Generate line-by-line diff
    lines1 = template1.splitlines()
    lines2 = template2.splitlines()
    diff_lines = list(
        difflib.unified_diff(
            lines1, lines2, fromfile="prompt1", tofile="prompt2", lineterm=""
        )
    )

    # Character-level differences for highlighting
    character_diff = _get_character_diff(template1, template2)

    return TemplateComparison(
        similarity_score=similarity,
        common_variables=common_variables,
        unique_to_first=unique_to_first,
        unique_to_second=unique_to_second,
        diff_lines=diff_lines,
        character_diff=character_diff,
    )


def _get_character_diff(text1: str, text2: str) -> List[Tuple[str, str]]:
    """Get character-level differences for highlighting."""
    diffs = []
    matcher = difflib.SequenceMatcher(None, text1, text2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "delete":
            diffs.append(("delete", text1[i1:i2]))
        elif tag == "insert":
            diffs.append(("insert", text2[j1:j2]))
        elif tag == "replace":
            diffs.append(("delete", text1[i1:i2]))
            diffs.append(("insert", text2[j1:j2]))

    return diffs


def _calculate_overall_similarity(
    prompt1: Prompt, prompt2: Prompt, template_comparison: TemplateComparison
) -> float:
    """Calculate overall similarity score."""
    weights = {
        "template": 0.4,
        "task": 0.15,
        "domain": 0.1,
        "prompt_strategy": 0.1,
        "prompt_type": 0.1,
        "model_config": 0.05,
        "target_models": 0.05,
        "variables": 0.05,
    }

    similarity_score = 0.0

    # Template similarity (most important)
    similarity_score += (
        weights["template"] * template_comparison.similarity_score
    )

    # Field similarities
    if prompt1.task == prompt2.task:
        similarity_score += weights["task"]
    elif prompt1.task and prompt2.task:
        # Partial similarity for related tasks
        related_tasks = {
            ("qa", "question_answering"): 0.8,
            ("classification", "categorization"): 0.8,
            ("generation", "creative_writing"): 0.6,
        }
        pair = (prompt1.task, prompt2.task)
        if pair in related_tasks or pair[::-1] in related_tasks:
            similarity_score += weights["task"] * related_tasks.get(
                pair, related_tasks.get(pair[::-1], 0)
            )

    # Domain similarity
    if prompt1.domain == prompt2.domain:
        similarity_score += weights["domain"]

    # Strategy similarity
    if prompt1.prompt_strategy == prompt2.prompt_strategy:
        similarity_score += weights["prompt_strategy"]

    # Prompt type similarity
    if prompt1.prompt_type == prompt2.prompt_type:
        similarity_score += weights["prompt_type"]

    # Model config similarity
    if prompt1.model_config_params == prompt2.model_config_params:
        similarity_score += weights["model_config"]
    elif prompt1.model_config_params and prompt2.model_config_params:
        # Partial similarity based on common parameters
        common_params = set(prompt1.model_config_params.keys()).intersection(
            set(prompt2.model_config_params.keys())
        )
        if common_params:
            similarity_score += weights["model_config"] * 0.5

    # Target models similarity
    if prompt1.target_models == prompt2.target_models:
        similarity_score += weights["target_models"]
    elif prompt1.target_models and prompt2.target_models:
        # Partial similarity based on overlap
        overlap = len(
            set(prompt1.target_models).intersection(set(prompt2.target_models))
        )
        total = len(
            set(prompt1.target_models).union(set(prompt2.target_models))
        )
        similarity_score += weights["target_models"] * (overlap / total)

    # Variables similarity
    if prompt1.variables == prompt2.variables:
        similarity_score += weights["variables"]
    elif prompt1.variables and prompt2.variables:
        # Partial similarity based on common variables
        common_vars = set(prompt1.variables.keys()).intersection(
            set(prompt2.variables.keys())
        )
        if common_vars:
            similarity_score += weights["variables"] * 0.5

    return min(similarity_score, 1.0)


def _check_compatibility(
    prompt1: Prompt, prompt2: Prompt, differences: List[PromptDiff]
) -> bool:
    """Check if prompts are compatible for A/B testing."""
    # Incompatible if different tasks
    if prompt1.task != prompt2.task and prompt1.task and prompt2.task:
        return False

    # Incompatible if very different domains
    incompatible_domains = [
        ("medical", "legal"),
        ("technical", "creative"),
        ("academic", "conversational"),
    ]

    if prompt1.domain and prompt2.domain:
        domain_pair = (prompt1.domain, prompt2.domain)
        if (
            domain_pair in incompatible_domains
            or domain_pair[::-1] in incompatible_domains
        ):
            return False

    # Incompatible if too many critical differences
    critical_differences = [
        diff
        for diff in differences
        if diff.field in ["task", "domain", "prompt_type", "expected_format"]
    ]

    if len(critical_differences) > 2:
        return False

    return True


def _compare_performance(
    prompt1: Prompt, prompt2: Prompt
) -> Optional[Dict[str, Dict[str, float]]]:
    """Compare performance metrics between prompts."""
    if not prompt1.performance_metrics or not prompt2.performance_metrics:
        return None

    comparison = {}

    # Get all metrics
    all_metrics = set(prompt1.performance_metrics.keys()).union(
        set(prompt2.performance_metrics.keys())
    )

    for metric in all_metrics:
        value1 = prompt1.performance_metrics.get(metric)
        value2 = prompt2.performance_metrics.get(metric)

        if value1 is not None and value2 is not None:
            comparison[metric] = {
                "prompt1": value1,
                "prompt2": value2,
                "difference": value2 - value1,
                "improvement": ((value2 - value1) / value1) * 100
                if value1 != 0
                else 0,
            }

    return comparison if comparison else None


def find_similar_prompts(
    target_prompt: Prompt,
    prompt_candidates: List[Prompt],
    similarity_threshold: float = 0.7,
) -> List[Tuple[Prompt, float]]:
    """Find prompts similar to the target prompt.

    Args:
        target_prompt: Prompt to find similarities for
        prompt_candidates: List of prompts to search through
        similarity_threshold: Minimum similarity score to include

    Returns:
        List of (prompt, similarity_score) tuples, sorted by similarity
    """
    similar_prompts = []

    for candidate in prompt_candidates:
        if candidate.prompt_id == target_prompt.prompt_id:
            continue

        comparison = compare_prompts(target_prompt, candidate)

        if comparison.overall_similarity >= similarity_threshold:
            similar_prompts.append((candidate, comparison.overall_similarity))

    # Sort by similarity (highest first)
    similar_prompts.sort(key=lambda x: x[1], reverse=True)

    return similar_prompts


def generate_comparison_report(comparison: PromptComparison) -> str:
    """Generate a human-readable comparison report.

    Args:
        comparison: PromptComparison object

    Returns:
        Formatted report string
    """
    report = []

    # Header
    report.append("# Prompt Comparison Report")
    report.append(f"Comparison performed at: {comparison.compared_at}")
    report.append(f"Overall Similarity: {comparison.overall_similarity:.2%}")
    report.append(
        f"Compatible for A/B Testing: {'Yes' if comparison.is_compatible else 'No'}"
    )
    report.append("")

    # Summary
    summary = comparison.get_summary()
    report.append("## Summary")
    report.append(f"- Total differences: {summary['total_differences']}")
    report.append(
        f"- Template similarity: {summary['template_similarity']:.2%}"
    )
    report.append(f"- Major differences: {len(summary['major_differences'])}")
    report.append("")

    # Recommendation
    report.append("## Recommendation")
    report.append(comparison.get_recommendation())
    report.append("")

    # Differences
    if comparison.differences:
        report.append("## Differences")
        for diff in comparison.differences:
            report.append(f"- **{diff.field}** ({diff.diff_type})")
            report.append(f"  - Prompt 1: {diff.prompt1_value}")
            report.append(f"  - Prompt 2: {diff.prompt2_value}")
        report.append("")

    # Template comparison
    template = comparison.template_comparison
    report.append("## Template Analysis")
    report.append(f"- Similarity: {template.similarity_score:.2%}")
    report.append(
        f"- Common variables: {', '.join(template.common_variables) if template.common_variables else 'None'}"
    )

    if template.unique_to_first:
        report.append(
            f"- Variables only in Prompt 1: {', '.join(template.unique_to_first)}"
        )
    if template.unique_to_second:
        report.append(
            f"- Variables only in Prompt 2: {', '.join(template.unique_to_second)}"
        )

    # Performance comparison
    if comparison.performance_comparison:
        report.append("")
        report.append("## Performance Comparison")
        for metric, data in comparison.performance_comparison.items():
            improvement = data["improvement"]
            symbol = (
                "↑" if improvement > 0 else "↓" if improvement < 0 else "="
            )
            report.append(
                f"- **{metric}**: {data['prompt1']:.3f} → {data['prompt2']:.3f} ({symbol} {abs(improvement):.1f}%)"
            )

    return "\n".join(report)
