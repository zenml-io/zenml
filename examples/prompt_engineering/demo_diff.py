#!/usr/bin/env python3
"""Demo script showing ZenML's core GitHub-style prompt diffing functionality."""

from zenml.prompts import (
    Prompt,
    PromptType,
    compare_text_outputs,
    format_diff_for_console,
)

# Create two different prompt versions
prompt_v1 = Prompt(
    template="""Please summarize the following text in 2-3 sentences:

Text: {article}

Summary:""",
    prompt_type=PromptType.USER,
    variables={"article": ""},
)

prompt_v2 = Prompt(
    template="""You are an expert summarizer. Please provide a concise summary of the following text, 
highlighting the key concepts and main ideas in exactly 2 sentences:

Article: {article}

Key Summary:""",
    prompt_type=PromptType.USER,
    variables={"article": ""},
)


def demo_prompt_diff():
    """Demonstrate ZenML's core GitHub-style prompt comparison."""
    print("🔍 ZENML CORE PROMPT COMPARISON DEMO")
    print("=" * 50)

    # Use ZenML's core diff method
    print("✨ Using prompt1.diff(prompt2) - Core ZenML functionality:")
    diff_result = prompt_v1.diff(prompt_v2, "V1", "V2")

    print("\n📊 DIFF STATISTICS:")
    template_stats = diff_result["template_diff"]["stats"]
    print(f"Template similarity: {template_stats['similarity_ratio']:.1%}")
    print(f"Added lines: {template_stats['added_lines']}")
    print(f"Removed lines: {template_stats['removed_lines']}")
    print(f"Total changes: {template_stats['total_changes']}")

    print("\n📝 COLORED UNIFIED DIFF:")
    colored_diff = format_diff_for_console(
        diff_result["template_diff"], color=True
    )
    print(colored_diff)

    print("\n📋 SUMMARY:")
    summary = diff_result["summary"]
    print(f"Template changed: {summary['template_changed']}")
    print(f"Variables changed: {summary['variables_changed']}")
    print(f"Type changed: {summary['type_changed']}")
    print(f"Prompts identical: {summary['identical']}")

    return diff_result


def demo_output_comparison():
    """Demo comparing actual outputs from different prompts."""
    print("\n🔄 OUTPUT COMPARISON DEMO")
    print("=" * 50)

    # Simulate different outputs from each prompt
    v1_outputs = [
        "Article discusses AI trends. Main points are automation and job impact.",
        "The research covers machine learning applications in healthcare and finance.",
    ]

    v2_outputs = [
        "The article explores current artificial intelligence trends with focus on automation. It emphasizes the significant impact on employment and job market transformation.",
        "This research comprehensively examines machine learning applications across healthcare and financial sectors. The study highlights implementation challenges and potential benefits.",
    ]

    # Use ZenML's core output comparison
    output_comparison = compare_text_outputs(
        v1_outputs, v2_outputs, "V1", "V2"
    )

    if output_comparison["comparable"]:
        stats = output_comparison["aggregate_stats"]
        print(f"📈 Average similarity: {stats['average_similarity']:.2%}")
        print(f"🔢 Total outputs: {stats['total_outputs']}")
        print(f"🔄 Changed outputs: {stats['changed_outputs']}")
        print(f"✅ Identical outputs: {stats['identical_outputs']}")

        for i, comp in enumerate(output_comparison["comparisons"]):
            print(f"\n📄 COMPARISON {i + 1}:")
            print(f"Similarity: {comp['similarity']:.2%}")
            print("Changes:")
            for change_type, line in comp["diff"]["side_by_side"][
                :3
            ]:  # Show first 3 lines
                if change_type == "added":
                    print(f"  + {line}")
                elif change_type == "removed":
                    print(f"  - {line}")


if __name__ == "__main__":
    # Run the demos
    diff_result = demo_prompt_diff()
    demo_output_comparison()

    print("\n✅ Demo complete!")
    print("\n🎯 KEY TAKEAWAYS:")
    print("• prompt1.diff(prompt2) - Core ZenML method for prompt comparison")
    print("• compare_text_outputs() - Compare LLM outputs with diffs")
    print("• create_text_diff() - General text diffing utility")
    print("• format_diff_for_console() - Pretty console output with colors")
    print("\n💡 These are core ZenML functions - no custom steps needed!")
    print("   Available everywhere: in pipelines, UI, notebooks, scripts.")
