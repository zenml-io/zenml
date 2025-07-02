"""Steps for evaluating prompt performance and responses."""

from typing import Annotated, Dict, List

from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


@step
def evaluate_prompt_response(
    prompt: Prompt, response: str
) -> Annotated[
    Dict[str, float],
    ArtifactConfig(name="evaluation_metrics", tags=["evaluation", "metrics"]),
]:
    """Evaluate the quality and characteristics of a prompt response."""

    metrics = {}

    # Basic response metrics
    metrics["response_length"] = len(response)
    metrics["word_count"] = len(response.split())
    metrics["sentence_count"] = len(
        [s for s in response.split(".") if s.strip()]
    )

    # Content analysis
    metrics["completeness_score"] = calculate_completeness_score(
        prompt, response
    )
    metrics["relevance_score"] = calculate_relevance_score(prompt, response)
    metrics["format_compliance"] = calculate_format_compliance(
        prompt, response
    )

    # Task-specific metrics
    if prompt.task == "question_answering":
        metrics.update(evaluate_qa_response(prompt, response))
    elif prompt.task == "conversation":
        metrics.update(evaluate_conversational_response(prompt, response))
    elif prompt.task == "interview":
        metrics.update(evaluate_interview_response(prompt, response))
    elif prompt.task == "analysis":
        metrics.update(evaluate_analysis_response(prompt, response))

    # Prompt strategy evaluation
    if prompt.prompt_strategy:
        metrics.update(evaluate_strategy_effectiveness(prompt, response))

    # Model configuration impact
    if prompt.model_config_params:
        metrics["temperature_used"] = prompt.model_config_params.get(
            "temperature", 0.5
        )
        metrics["max_tokens_used"] = prompt.model_config_params.get(
            "max_tokens", 1000
        )
        metrics["token_efficiency"] = metrics[
            "word_count"
        ] / prompt.model_config_params.get("max_tokens", 1000)

    # Overall quality score (weighted average)
    metrics["overall_quality"] = (
        metrics["completeness_score"] * 0.3
        + metrics["relevance_score"] * 0.3
        + metrics["format_compliance"] * 0.2
        + metrics.get("clarity_score", 0.8) * 0.2
    )

    logger.info(
        f"Evaluation completed with overall quality: {metrics['overall_quality']:.2f}"
    )
    return metrics


@step
def evaluate_multiple_responses(
    prompts: List[Prompt], responses: List[str]
) -> Annotated[
    List[Dict[str, float]],
    ArtifactConfig(
        name="multiple_evaluations", tags=["evaluation", "comparison"]
    ),
]:
    """Evaluate multiple prompt-response pairs."""

    evaluations = []
    for i, (prompt, response) in enumerate(zip(prompts, responses)):
        logger.info(f"Evaluating response {i + 1}/{len(responses)}")
        evaluation = evaluate_prompt_response.entrypoint(prompt, response)
        evaluations.append(evaluation)

    # Add comparative metrics
    overall_scores = [eval["overall_quality"] for eval in evaluations]
    for i, evaluation in enumerate(evaluations):
        evaluation["rank"] = (
            sorted(overall_scores, reverse=True).index(overall_scores[i]) + 1
        )
        evaluation["percentile"] = (
            len(overall_scores) - evaluation["rank"] + 1
        ) / len(overall_scores)

    logger.info("Multiple evaluations completed with rankings")
    return evaluations


def calculate_completeness_score(prompt: Prompt, response: str) -> float:
    """Calculate how complete the response is based on prompt requirements."""

    score = 0.5  # Base score

    # Check if response addresses the main question/topic
    if prompt.variables and "question" in prompt.variables:
        question_keywords = prompt.variables["question"].lower().split()
        response_lower = response.lower()
        keyword_matches = sum(
            1 for word in question_keywords if word in response_lower
        )
        score += (keyword_matches / len(question_keywords)) * 0.3

    # Check response length appropriateness
    if len(response) > 100:  # Reasonable length
        score += 0.2

    return min(score, 1.0)


def calculate_relevance_score(prompt: Prompt, response: str) -> float:
    """Calculate how relevant the response is to the prompt."""

    score = 0.6  # Base relevance

    # Check if task type is reflected in response
    task_keywords = {
        "question_answering": ["answer", "question", "response"],
        "conversation": ["think", "share", "discuss"],
        "interview": ["experience", "perspective", "insights"],
        "analysis": ["analysis", "conclusion", "findings"],
    }

    if prompt.task in task_keywords:
        keywords = task_keywords[prompt.task]
        response_lower = response.lower()
        matches = sum(1 for keyword in keywords if keyword in response_lower)
        score += (matches / len(keywords)) * 0.4

    return min(score, 1.0)


def calculate_format_compliance(prompt: Prompt, response: str) -> float:
    """Calculate how well the response follows expected format."""

    score = 0.7  # Base format score

    # Check for expected format elements
    if prompt.expected_format:
        if prompt.expected_format == "structured_response" and any(
            marker in response for marker in ["1.", "2.", "•", "-", "**"]
        ):
            score += 0.3
        elif prompt.expected_format == "markdown" and any(
            marker in response for marker in ["**", "#", "*", "-"]
        ):
            score += 0.3

    # Check if response follows prompt structure hints
    if any(structure in prompt.template for structure in ["1.", "2.", "3."]):
        if any(marker in response for marker in ["1.", "2.", "3."]):
            score += 0.2

    return min(score, 1.0)


def evaluate_qa_response(prompt: Prompt, response: str) -> Dict[str, float]:
    """Evaluate question-answering specific metrics."""

    metrics = {}

    # Check for direct answer
    metrics["has_direct_answer"] = (
        1.0
        if any(
            phrase in response.lower()
            for phrase in ["benefits", "advantages", "key"]
        )
        else 0.5
    )

    # Check for explanation depth
    metrics["explanation_depth"] = min(len(response.split(". ")) / 5, 1.0)

    # Check for examples
    metrics["includes_examples"] = (
        1.0
        if any(
            word in response.lower()
            for word in ["example", "such as", "like", "netflix", "amazon"]
        )
        else 0.3
    )

    # Clarity score based on structure
    metrics["clarity_score"] = (
        0.9
        if any(marker in response for marker in ["1.", "2.", "•", "-", "**"])
        else 0.6
    )

    return metrics


def evaluate_conversational_response(
    prompt: Prompt, response: str
) -> Dict[str, float]:
    """Evaluate conversational response metrics."""

    metrics = {}

    # Check conversational tone
    casual_indicators = ["hey", "great", "pretty", "awesome", "cool", "thing"]
    metrics["conversational_tone"] = min(
        sum(1 for word in casual_indicators if word in response.lower()) / 3,
        1.0,
    )

    # Check for engagement elements
    engagement_indicators = ["?", "!", "think", "right", "you"]
    metrics["engagement_level"] = min(
        sum(
            1
            for indicator in engagement_indicators
            if indicator in response.lower()
        )
        / 5,
        1.0,
    )

    # Check for personal touch
    metrics["personal_touch"] = (
        1.0
        if any(
            phrase in response.lower()
            for phrase in ["my", "i've", "experience", "think"]
        )
        else 0.4
    )

    metrics["clarity_score"] = (
        0.8  # Conversational responses are generally clear
    )

    return metrics


def evaluate_interview_response(
    prompt: Prompt, response: str
) -> Dict[str, float]:
    """Evaluate interview-style response metrics."""

    metrics = {}

    # Check for experience indicators
    experience_indicators = [
        "years",
        "experience",
        "i've seen",
        "my team",
        "we",
    ]
    metrics["experience_authority"] = min(
        sum(
            1
            for indicator in experience_indicators
            if indicator in response.lower()
        )
        / 3,
        1.0,
    )

    # Check for specific examples
    metrics["concrete_examples"] = (
        1.0
        if any(
            word in response.lower()
            for word in ["netflix", "amazon", "google", "system", "project"]
        )
        else 0.5
    )

    # Check for advice/recommendations
    metrics["actionability"] = (
        1.0
        if any(
            phrase in response.lower()
            for phrase in ["advice", "recommend", "should", "start"]
        )
        else 0.6
    )

    metrics["clarity_score"] = 0.85  # Interview responses are typically clear

    return metrics


def evaluate_analysis_response(
    prompt: Prompt, response: str
) -> Dict[str, float]:
    """Evaluate analytical response metrics."""

    metrics = {}

    # Check for analytical structure
    analytical_markers = [
        "analysis",
        "summary",
        "conclusion",
        "assessment",
        "findings",
    ]
    metrics["analytical_structure"] = min(
        sum(1 for marker in analytical_markers if marker in response.lower())
        / 3,
        1.0,
    )

    # Check for balanced perspective
    metrics["balance"] = (
        1.0
        if all(word in response.lower() for word in ["benefits", "advantages"])
        else 0.7
    )

    # Check for evidence/support
    metrics["evidence_support"] = (
        1.0
        if any(
            word in response.lower()
            for word in ["data", "research", "study", "evidence"]
        )
        else 0.6
    )

    metrics["clarity_score"] = 0.9  # Analytical responses should be clear

    return metrics


def evaluate_strategy_effectiveness(
    prompt: Prompt, response: str
) -> Dict[str, float]:
    """Evaluate how well the prompt strategy was executed."""

    metrics = {}

    strategy_checks = {
        "structured": lambda r: len(
            [
                line
                for line in r.split("\n")
                if line.strip().startswith(("1.", "2.", "3.", "•", "-"))
            ]
        )
        > 2,
        "conversational": lambda r: sum(
            1 for word in ["hey", "think", "you", "great"] if word in r.lower()
        )
        > 1,
        "direct": lambda r: len(r.split()) < 200,  # Concise response
        "pros_cons": lambda r: "pros" in r.lower() and "cons" in r.lower(),
        "role_playing": lambda r: any(
            phrase in r.lower() for phrase in ["experience", "i've", "my"]
        ),
    }

    if prompt.prompt_strategy in strategy_checks:
        metrics["strategy_effectiveness"] = (
            1.0 if strategy_checks[prompt.prompt_strategy](response) else 0.4
        )
    else:
        metrics["strategy_effectiveness"] = (
            0.7  # Default for unknown strategies
        )

    return metrics
