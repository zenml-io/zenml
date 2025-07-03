"""Simple example of prompt evaluation using ZenML's LLM-as-Judge framework.

This is a minimal example that demonstrates how to:
1. Create prompt artifacts
2. Evaluate their quality
3. Compare different versions

Run this example with: python simple_evaluation.py
"""

from typing import Dict, List, Any
from zenml import step, pipeline
from zenml.client import Client
from zenml.steps.prompt_evaluation import llm_judge_evaluate_prompt, compare_prompt_versions


@step
def create_sample_prompts() -> List[str]:
    """Create sample prompt artifacts for evaluation."""
    from zenml.artifacts.utils import save_artifact
    
    # Basic prompt
    basic_prompt = """Answer the user's question: {question}"""
    
    # Improved prompt with better structure
    improved_prompt = """You are a helpful AI assistant.

User Question: {question}
Context: {context}

Please provide a clear, accurate, and helpful response. Consider the user's level of expertise and provide explanations as needed.

Response:"""
    
    # Save as ZenML artifacts
    basic_artifact = save_artifact(
        data=basic_prompt,
        name="basic_qa_prompt", 
        artifact_type="prompt",
        metadata={
            "version": "1.0",
            "complexity": "basic",
            "variable_count": 1
        }
    )
    
    improved_artifact = save_artifact(
        data=improved_prompt,
        name="improved_qa_prompt",
        artifact_type="prompt", 
        metadata={
            "version": "2.0",
            "complexity": "structured",
            "variable_count": 2
        }
    )
    
    return [basic_artifact.id, improved_artifact.id]


@step
def create_test_cases() -> List[Dict[str, Any]]:
    """Create test cases for evaluation."""
    return [
        {
            "variables": {
                "question": "What is machine learning?",
                "context": "The user is a complete beginner to AI/ML"
            },
            "expected_output": "A beginner-friendly explanation of machine learning concepts"
        },
        {
            "variables": {
                "question": "How do I deploy a ML model to production?",
                "context": "The user is a software developer with some ML experience"
            },
            "expected_output": "Practical guidance on ML model deployment strategies"
        },
        {
            "variables": {
                "question": "What's the difference between supervised and unsupervised learning?",
                "context": "The user is studying data science"
            },
            "expected_output": "Clear explanation with examples of both learning types"
        }
    ]


@step
def evaluate_prompt_quality(
    prompt_id: str,
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluate a single prompt using LLM-as-Judge."""
    
    evaluation_criteria = [
        "relevance",    # How relevant is the response to the question
        "clarity",      # How clear and understandable the response is
        "accuracy",     # Technical accuracy of the information
        "helpfulness"   # How helpful the response is to the user
    ]
    
    return llm_judge_evaluate_prompt(
        prompt_artifact_id=prompt_id,
        test_cases=test_cases,
        evaluation_criteria=evaluation_criteria,
        judge_model="gpt-4",  # Use best available model for evaluation
        temperature=0.1       # Low temperature for consistent evaluation
    )


@step
def compare_prompts(
    prompt1_id: str,
    prompt2_id: str, 
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare two prompt versions."""
    
    evaluation_criteria = ["relevance", "clarity", "accuracy", "helpfulness"]
    
    return compare_prompt_versions(
        prompt_v1_id=prompt1_id,
        prompt_v2_id=prompt2_id,
        test_cases=test_cases,
        evaluation_criteria=evaluation_criteria,
        judge_model="gpt-4"
    )


@step
def print_results(
    evaluations: List[Dict[str, Any]],
    comparison: Dict[str, Any]
) -> None:
    """Print evaluation results in a readable format."""
    
    print("\n" + "="*60)
    print("PROMPT EVALUATION RESULTS")
    print("="*60)
    
    # Individual evaluations
    for i, eval_result in enumerate(evaluations, 1):
        print(f"\nPrompt {i} Results:")
        print(f"  Overall Score: {eval_result['overall_score']:.2f}/1.0")
        print(f"  Quality Level: {eval_result['quality_level']}")
        print(f"  Test Cases: {eval_result['test_cases_count']}")
        
        print("  Criteria Scores:")
        for criterion, score in eval_result['average_scores'].items():
            print(f"    {criterion.title()}: {score:.2f}")
        
        if eval_result['recommendations']:
            print("  Recommendations:")
            for rec in eval_result['recommendations']:
                print(f"    • {rec}")
    
    # Comparison results
    print(f"\n{'-'*40}")
    print("COMPARISON RESULTS")
    print(f"{'-'*40}")
    
    if comparison['winner'] == 'tie':
        print("Result: The prompts performed equally well")
    else:
        winner_num = "1" if comparison['winner'] == 'v1' else "2" 
        print(f"Winner: Prompt {winner_num}")
        print(f"Improvement: {comparison['improvement_percentage']:.1f}%")
        print(f"Score Difference: {comparison['score_difference']:.3f}")
    
    print("\nDetailed Comparison:")
    for criterion, details in comparison['detailed_comparison'].items():
        v1_score = details['v1_score']
        v2_score = details['v2_score']
        winner = details['winner']
        
        print(f"  {criterion.title()}:")
        print(f"    Prompt 1: {v1_score:.2f} | Prompt 2: {v2_score:.2f}")
        
        if winner == 'tie':
            print("    Result: Tie")
        else:
            winner_num = "1" if winner == 'v1' else "2"
            print(f"    Winner: Prompt {winner_num}")


@pipeline
def simple_prompt_evaluation() -> None:
    """Simple pipeline demonstrating prompt evaluation."""
    
    # Create sample prompts
    prompt_ids = create_sample_prompts()
    
    # Create test cases
    test_cases = create_test_cases()
    
    # Evaluate both prompts
    eval1 = evaluate_prompt_quality(prompt_ids[0], test_cases)
    eval2 = evaluate_prompt_quality(prompt_ids[1], test_cases)
    
    # Compare the prompts
    comparison = compare_prompts(prompt_ids[0], prompt_ids[1], test_cases)
    
    # Print results
    print_results([eval1, eval2], comparison)


if __name__ == "__main__":
    print("Starting simple prompt evaluation example...")
    print("\nThis example will:")
    print("1. Create two sample prompt artifacts")
    print("2. Evaluate their quality using LLM-as-Judge")
    print("3. Compare the prompts to identify the better version")
    print("\nNote: This requires an OpenAI API key set in OPENAI_API_KEY environment variable")
    
    # Check if we can access ZenML
    try:
        client = Client()
        print(f"✓ Connected to ZenML (Active stack: {client.active_stack.name})")
    except Exception as e:
        print(f"✗ Failed to connect to ZenML: {e}")
        print("Make sure ZenML is installed and configured (run 'zenml up')")
        exit(1)
    
    # Run the evaluation pipeline
    try:
        simple_prompt_evaluation()
        print("\n✓ Evaluation completed successfully!")
        print("\nNext steps:")
        print("- Try modifying the prompts to see how scores change")
        print("- Add more test cases for comprehensive evaluation")
        print("- Experiment with different evaluation criteria")
        print("- Use the ZenML Cloud UI to visualize results")
        
    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}")
        print("\nTroubleshooting:")
        print("- Ensure OPENAI_API_KEY environment variable is set")
        print("- Check that you have sufficient OpenAI credits")
        print("- Verify ZenML server is running ('zenml status')")