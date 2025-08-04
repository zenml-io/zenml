"""Utility functions for prompt engineering workflows."""

from typing import Any, Dict, List


def format_comparison_results(results: dict) -> str:
    """Format comparison results for display.

    Args:
        results: Results dictionary from comparison step

    Returns:
        Formatted string for console output
    """
    winner = results["winner"]
    scores = results["scores"]

    output = []
    output.append("🏆 Prompt Comparison Results")
    output.append("=" * 30)
    output.append(f"Winner: Version {winner}")
    output.append(f"V1.0 Average Score: {scores['v1_average']:.1f}")
    output.append(f"V2.0 Average Score: {scores['v2_average']:.1f}")
    output.append("")
    output.append("Individual Test Results:")

    for i, question in enumerate(results["test_questions"]):
        v1_score = scores["v1_scores"][i]
        v2_score = scores["v2_scores"][i]
        test_winner = "V2.0" if v2_score > v1_score else "V1.0"
        output.append(
            f"  Q{i+1}: V1.0={v1_score}, V2.0={v2_score} → {test_winner}"
        )

    return "\n".join(output)


def create_test_questions(domain: str = "general") -> List[str]:
    """Generate test questions for prompt evaluation.

    Args:
        domain: Domain for test questions (general, technical, etc.)

    Returns:
        List of test questions
    """
    question_sets = {
        "general": [
            "What is machine learning?",
            "How does artificial intelligence work?",
            "What is the difference between AI and ML?",
        ],
        "technical": [
            "Explain neural networks in simple terms",
            "What is gradient descent?",
            "How does backpropagation work?",
        ],
        "business": [
            "How can AI improve business operations?",
            "What are the ROI benefits of machine learning?",
            "How do you implement AI in a company?",
        ],
    }

    return question_sets.get(domain, question_sets["general"])


def calculate_improvement_percentage(
    old_score: float, new_score: float
) -> float:
    """Calculate percentage improvement between scores.

    Args:
        old_score: Previous score
        new_score: New score

    Returns:
        Percentage improvement (can be negative)
    """
    if old_score == 0:
        return 100.0 if new_score > 0 else 0.0

    return ((new_score - old_score) / old_score) * 100


def validate_prompt_template(template: str) -> Dict[str, Any]:
    """Validate a prompt template for common issues.

    Args:
        template: The template string to validate

    Returns:
        Validation results with warnings and suggestions
    """
    issues = []
    suggestions = []

    # Check for variables
    import re

    variables = re.findall(r"\{([^}]+)\}", template)

    if not variables:
        issues.append("No variables found in template")
        suggestions.append(
            "Consider adding variables like {question} or {context}"
        )

    # Check template length
    if len(template) < 10:
        issues.append("Template seems very short")
        suggestions.append("Consider adding more context or instructions")
    elif len(template) > 1000:
        issues.append("Template is very long")
        suggestions.append("Consider breaking into smaller, focused prompts")

    # Check for clear instructions
    instruction_words = [
        "answer",
        "explain",
        "describe",
        "provide",
        "generate",
    ]
    has_instructions = any(
        word in template.lower() for word in instruction_words
    )

    if not has_instructions:
        issues.append("No clear instructions found")
        suggestions.append(
            "Add clear action words like 'explain', 'answer', or 'describe'"
        )

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "variables_found": variables,
        "template_length": len(template),
    }
