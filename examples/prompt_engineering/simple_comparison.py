#!/usr/bin/env python3
"""Simple prompt comparison utility - what users actually want."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from typing import Any, Dict, List, Callable
from zenml.prompts import Prompt

def compare_prompts_simple(
    prompt_a: Prompt,
    prompt_b: Prompt,
    test_cases: List[Dict[str, Any]],
    metric_function: Callable[[str], float]
) -> Dict[str, Any]:
    """Simple A/B prompt comparison - exactly what users need.
    
    Args:
        prompt_a: First prompt to test
        prompt_b: Second prompt to test  
        test_cases: List of test case dictionaries
        metric_function: Function that scores prompt outputs (higher = better)
        
    Returns:
        Comparison results with winner and metrics
    """
    print(f"🔄 Comparing Prompt v{prompt_a.version} vs v{prompt_b.version}")
    
    results_a = []
    results_b = []
    
    for i, test_case in enumerate(test_cases):
        # Format both prompts with test case
        try:
            formatted_a = prompt_a.format(**test_case)
            formatted_b = prompt_b.format(**test_case)
            
            # In real use, these would go to LLM and get responses
            # For demo, we'll simulate scoring the formatted prompts
            score_a = metric_function(formatted_a)
            score_b = metric_function(formatted_b)
            
            results_a.append(score_a)
            results_b.append(score_b)
            
            print(f"  Test {i+1:2d}: A={score_a:.2f} B={score_b:.2f}")
            
        except Exception as e:
            print(f"  Test {i+1:2d}: Error formatting prompts: {e}")
            continue
    
    # Calculate averages
    avg_a = sum(results_a) / len(results_a) if results_a else 0
    avg_b = sum(results_b) / len(results_b) if results_b else 0
    
    winner = "A" if avg_a > avg_b else "B"
    
    comparison = {
        "prompt_a_version": prompt_a.version,
        "prompt_b_version": prompt_b.version,
        "prompt_a_avg_score": avg_a,
        "prompt_b_avg_score": avg_b,
        "winner": winner,
        "margin": abs(avg_a - avg_b),
        "test_count": len(results_a),
        "detailed_results": {
            "prompt_a_scores": results_a,
            "prompt_b_scores": results_b
        }
    }
    
    return comparison

def demo_simple_prompt_comparison():
    """Demonstrate simple prompt comparison workflow."""
    print("🎯 Simple Prompt Comparison Demo")
    print("=" * 50)
    
    # Create two prompt versions
    prompt_v1 = Prompt(
        template="Answer: {question}",
        version="1.0.0"
    )
    
    prompt_v2 = Prompt(
        template="Please provide a thoughtful answer to this question: {question}",
        version="2.0.0"
    )
    
    # Test cases
    test_cases = [
        {"question": "What is machine learning?"},
        {"question": "How does AI work?"},
        {"question": "What is Python?"},
        {"question": "Explain data science"},
        {"question": "What is ZenML?"}
    ]
    
    # Simple metric: longer formatted prompts score higher (simulates more detailed prompts)
    def length_metric(formatted_prompt: str) -> float:
        """Simple demo metric: longer prompts score higher."""
        base_score = len(formatted_prompt) / 100.0
        # Add some randomness to simulate real LLM evaluation
        import random
        return base_score + random.uniform(-0.1, 0.1)
    
    # Run comparison
    result = compare_prompts_simple(
        prompt_a=prompt_v1,
        prompt_b=prompt_v2,
        test_cases=test_cases,
        metric_function=length_metric
    )
    
    # Display results
    print(f"\n🏆 COMPARISON RESULTS")
    print(f"Winner: Prompt v{result['winner']} ({result['prompt_a_version'] if result['winner'] == 'A' else result['prompt_b_version']})")
    print(f"Score A: {result['prompt_a_avg_score']:.3f}")
    print(f"Score B: {result['prompt_b_avg_score']:.3f}")
    print(f"Margin: {result['margin']:.3f}")
    print(f"Tests: {result['test_count']}")
    
    return result

if __name__ == "__main__":
    print("🚀 ZenML Simple Prompt Comparison Test")
    print("=" * 60)
    
    try:
        result = demo_simple_prompt_comparison()
        
        print("\n" + "=" * 60)
        print("✅ Simple A/B comparison works!")
        print("📊 This is exactly what users need:")
        print("   • Simple prompt version comparison")
        print("   • Metric-based evaluation") 
        print("   • Clear winner determination")
        print("   • No complex diff analysis")
        
        print(f"\n💡 In real usage:")
        print(f"   • Test cases would be real user scenarios")
        print(f"   • Metric function would evaluate LLM responses")
        print(f"   • Results would show in ZenML dashboard")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)