"""Step for testing and comparing prompts."""

from typing import List

from zenml import step
from zenml.prompts import Prompt


@step
def compare_prompt_versions(prompt_v1: Prompt, prompt_v2: Prompt) -> dict:
    """Compare two prompt versions using simple A/B testing logic.
    
    Args:
        prompt_v1: First prompt version
        prompt_v2: Second prompt version
        
    Returns:
        Comparison results with winner determination
    """
    test_questions = [
        "What is machine learning?",
        "How does AI work?",
        "What is Python?"
    ]
    
    scores_v1 = []
    scores_v2 = []
    
    for question in test_questions:
        # Format prompts with test question
        result_v1 = prompt_v1.format(question=question)
        result_v2 = prompt_v2.format(question=question)
        
        # Simple metric: length (detailed responses score higher)
        score_v1 = len(result_v1)
        score_v2 = len(result_v2)
        
        scores_v1.append(score_v1)
        scores_v2.append(score_v2)
    
    # Calculate averages and determine winner
    avg_v1 = sum(scores_v1) / len(scores_v1)
    avg_v2 = sum(scores_v2) / len(scores_v2)
    winner = prompt_v2.version if avg_v2 > avg_v1 else prompt_v1.version
    
    return {
        "prompt_v1": prompt_v1,  # Dashboard visualization
        "prompt_v2": prompt_v2,  # Dashboard visualization
        "winner": winner,
        "scores": {
            "v1_average": avg_v1,
            "v2_average": avg_v2,
            "v1_scores": scores_v1,
            "v2_scores": scores_v2
        },
        "test_questions": test_questions
    }


@step 
def evaluate_single_prompt(prompt: Prompt, test_questions: List[str]) -> dict:
    """Evaluate a single prompt against test questions.
    
    Args:
        prompt: The prompt to evaluate
        test_questions: List of questions to test with
        
    Returns:
        Evaluation results
    """
    results = []
    
    for question in test_questions:
        formatted = prompt.format(question=question)
        score = len(formatted)  # Simple scoring metric
        results.append({
            "question": question,
            "formatted_prompt": formatted,
            "score": score
        })
    
    average_score = sum(r["score"] for r in results) / len(results)
    
    return {
        "prompt": prompt,
        "results": results,
        "average_score": average_score,
        "total_questions": len(test_questions)
    }