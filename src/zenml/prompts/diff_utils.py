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
"""Core utilities for comparing prompts with GitHub-style diffs."""

import difflib
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from zenml.prompts.prompt import Prompt


def create_text_diff(
    text1: str,
    text2: str,
    name1: str = "Version 1",
    name2: str = "Version 2",
    context_lines: int = 3,
) -> Dict[str, Any]:
    """Create GitHub-style text diff between two text strings.

    Args:
        text1: First text to compare
        text2: Second text to compare
        name1: Name for first text (default: "Version 1")
        name2: Name for second text (default: "Version 2")
        context_lines: Number of context lines around changes

    Returns:
        Dictionary containing different diff formats and statistics
    """
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)

    # Create unified diff (like `git diff`)
    unified_diff = list(
        difflib.unified_diff(
            lines1,
            lines2,
            fromfile=name1,
            tofile=name2,
            lineterm="",
            n=context_lines,
        )
    )

    # Create HTML diff for dashboard visualization
    html_diff = difflib.HtmlDiff(wrapcolumn=100)
    html_comparison = html_diff.make_file(
        lines1,
        lines2,
        fromdesc=name1,
        todesc=name2,
        context=True,
        numlines=context_lines,
    )

    # Create side-by-side comparison data for custom UI
    side_by_side = []
    for line in difflib.unified_diff(
        lines1, lines2, lineterm="", n=context_lines
    ):
        if line.startswith("@@"):
            side_by_side.append(("context", line))
        elif line.startswith("-"):
            side_by_side.append(("removed", line[1:].rstrip()))
        elif line.startswith("+"):
            side_by_side.append(("added", line[1:].rstrip()))
        elif not line.startswith(("---", "+++")):
            side_by_side.append(("unchanged", line.rstrip()))

    # Calculate diff statistics
    added_lines = sum(
        1
        for line in unified_diff
        if line.startswith("+") and not line.startswith("+++")
    )
    removed_lines = sum(
        1
        for line in unified_diff
        if line.startswith("-") and not line.startswith("---")
    )

    # Calculate similarity ratio
    similarity = difflib.SequenceMatcher(None, text1, text2).ratio()

    return {
        "unified_diff": "\n".join(unified_diff),
        "html_diff": html_comparison,
        "side_by_side": side_by_side,
        "similarity": similarity,
        "stats": {
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "total_changes": added_lines + removed_lines,
            "similarity_ratio": similarity,
            "identical": similarity == 1.0,
        },
    }


def compare_prompts(
    prompt1: "Prompt",
    prompt2: "Prompt",
    name1: Optional[str] = None,
    name2: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare two Prompt objects with comprehensive diff analysis.

    Args:
        prompt1: First prompt to compare
        prompt2: Second prompt to compare
        name1: Optional name for first prompt (defaults to "Prompt 1")
        name2: Optional name for second prompt (defaults to "Prompt 2")

    Returns:
        Comprehensive comparison with text diffs and metadata analysis
    """
    name1 = name1 or "Prompt 1"
    name2 = name2 or "Prompt 2"

    # Compare prompt templates
    template_diff = create_text_diff(
        prompt1.template,
        prompt2.template,
        f"{name1} Template",
        f"{name2} Template",
    )

    # Compare variables if they exist
    variables_diff = None
    if prompt1.variables != prompt2.variables:
        var1_str = str(prompt1.variables)
        var2_str = str(prompt2.variables)
        variables_diff = create_text_diff(
            var1_str, var2_str, f"{name1} Variables", f"{name2} Variables"
        )

    # Compare prompt types
    type_changed = prompt1.prompt_type != prompt2.prompt_type

    return {
        "prompt1": prompt1,
        "prompt2": prompt2,
        "template_diff": template_diff,
        "variables_diff": variables_diff,
        "metadata_changes": {
            "type_changed": type_changed,
            "old_type": prompt1.prompt_type.value
            if hasattr(prompt1.prompt_type, "value")
            else str(prompt1.prompt_type),
            "new_type": prompt2.prompt_type.value
            if hasattr(prompt2.prompt_type, "value")
            else str(prompt2.prompt_type),
            "variables_changed": variables_diff is not None,
        },
        "summary": {
            "template_changed": template_diff["stats"]["total_changes"] > 0,
            "variables_changed": variables_diff is not None,
            "type_changed": type_changed,
            "total_template_changes": template_diff["stats"]["total_changes"],
            "template_similarity": template_diff["stats"]["similarity_ratio"],
            "identical": (
                template_diff["stats"]["identical"]
                and not variables_diff
                and not type_changed
            ),
        },
    }


def compare_text_outputs(
    outputs1: List[str],
    outputs2: List[str],
    name1: str = "Version 1",
    name2: str = "Version 2",
) -> Dict[str, Any]:
    """Compare two lists of text outputs (e.g., LLM responses).

    Args:
        outputs1: List of outputs from first version
        outputs2: List of outputs from second version
        name1: Name for first version
        name2: Name for second version

    Returns:
        Comparison analysis of the outputs with diffs and similarity metrics
    """
    if len(outputs1) != len(outputs2):
        return {
            "error": f"Output counts don't match: {len(outputs1)} vs {len(outputs2)}",
            "comparable": False,
            "output_count_mismatch": True,
        }

    comparisons = []
    similarities = []

    for i, (out1, out2) in enumerate(zip(outputs1, outputs2)):
        diff = create_text_diff(
            out1, out2, f"{name1} Output {i+1}", f"{name2} Output {i+1}"
        )

        comparison = {
            "index": i,
            "output1": out1,
            "output2": out2,
            "diff": diff,
            "similarity": diff["similarity"],
            "identical": diff["stats"]["identical"],
        }

        comparisons.append(comparison)
        similarities.append(diff["similarity"])

    avg_similarity = (
        sum(similarities) / len(similarities) if similarities else 0.0
    )

    return {
        "comparable": True,
        "output_count_mismatch": False,
        "comparisons": comparisons,
        "aggregate_stats": {
            "total_outputs": len(outputs1),
            "average_similarity": avg_similarity,
            "identical_outputs": sum(
                1 for comp in comparisons if comp["identical"]
            ),
            "changed_outputs": sum(
                1 for comp in comparisons if not comp["identical"]
            ),
            "min_similarity": min(similarities) if similarities else 0.0,
            "max_similarity": max(similarities) if similarities else 0.0,
        },
    }


def format_diff_for_console(
    diff_result: Dict[str, Any], color: bool = True
) -> str:
    """Format diff result for console output with optional colors.

    Args:
        diff_result: Result from create_text_diff()
        color: Whether to include ANSI color codes

    Returns:
        Formatted string for console display
    """
    if not color:
        return diff_result["unified_diff"]

    # ANSI color codes
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    RESET = "\033[0m"

    lines = diff_result["unified_diff"].split("\n")
    colored_lines = []

    for line in lines:
        if line.startswith("---") or line.startswith("+++"):
            colored_lines.append(f"{BLUE}{line}{RESET}")
        elif line.startswith("@@"):
            colored_lines.append(f"{BLUE}{line}{RESET}")
        elif line.startswith("-"):
            colored_lines.append(f"{RED}{line}{RESET}")
        elif line.startswith("+"):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        else:
            colored_lines.append(line)

    return "\n".join(colored_lines)
