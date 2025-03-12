#!/usr/bin/env python3
"""Compare ZenML CLI performance profiles and generate a report.

This script compares the performance results from two different
branches and generates a detailed markdown report highlighting
performance differences, failures, and timeouts.
"""

import argparse
import json
import random
import sys


def load_json(filename):
    """Load JSON data from a file."""
    with open(filename, "r") as f:
        return json.load(f)


def get_motivational_message():
    """Return a random motivational message for performance improvements."""
    messages = [
        "🚀 Great job! Your changes have improved ZenML's performance!",
        "⚡ Amazing work on the performance improvements!",
        "🏎️ Need for speed? You've got it! Your changes make ZenML faster!",
        "⏱️ Time is money, and you just made ZenML users richer!",
        "💪 Strong performance optimization! The ZenML CLI thanks you!",
        "🔥 Your code is on fire (in a good way)! Performance is fantastic!",
        "🌠 Stellar performance improvements! Keep up the great work!",
        "⚙️ You've fine-tuned the ZenML engine to perfection!",
        "🧙 Performance wizardry at its finest!",
        "🎯 Bull's eye on performance targets! Well done!",
    ]
    return random.choice(messages)


def format_time_diff(target_time, current_time):
    """Format the time difference with appropriate signage and units."""
    diff = target_time - current_time
    if abs(diff) < 0.001:
        return "±0.000s"

    sign = "+" if diff < 0 else "-"  # + means slower, - means faster
    return f"{sign}{abs(diff):.3f}s"


def main():
    parser = argparse.ArgumentParser(
        description="Compare ZenML CLI performance profiles"
    )
    parser.add_argument(
        "--target-file",
        required=True,
        help="JSON file with target branch results",
    )
    parser.add_argument(
        "--current-file",
        required=True,
        help="JSON file with current branch results",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Time threshold in seconds for flagging degradation",
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="Command timeout in seconds"
    )
    parser.add_argument(
        "--target-branch", required=True, help="Name of the target branch"
    )
    parser.add_argument(
        "--current-branch", required=True, help="Name of the current branch"
    )
    parser.add_argument(
        "--output",
        default="performance_report.md",
        help="Output markdown file",
    )

    args = parser.parse_args()

    # Load results
    target_data = load_json(args.target_file)
    current_data = load_json(args.current_file)

    # Extract results
    target_results = {
        item["command"]: item for item in target_data["profiling_results"]
    }
    current_results = {
        item["command"]: item for item in current_data["profiling_results"]
    }

    # Start markdown report
    markdown = "<!-- PERFORMANCE_REPORT -->\n"
    markdown += f"## ZenML CLI Performance Comparison (Threshold: {args.threshold}s, Timeout: {args.timeout}s)\n\n"

    # Check for command failures and timeouts
    target_failures = [
        cmd
        for cmd, data in target_results.items()
        if data.get("status") == "failed"
    ]
    current_failures = [
        cmd
        for cmd, data in current_results.items()
        if data.get("status") == "failed"
    ]
    target_timeouts = [
        cmd
        for cmd, data in target_results.items()
        if data.get("status") == "timeout"
    ]
    current_timeouts = [
        cmd
        for cmd, data in current_results.items()
        if data.get("status") == "timeout"
    ]

    has_issues = False

    # Check failures on target branch
    if target_failures:
        markdown += f"### ⚠️ Failed Commands on Target Branch ({args.target_branch})\n\n"
        for cmd in target_failures:
            markdown += f"- `{cmd}`: {target_results[cmd].get('error', 'Unknown error')}\n"
        markdown += "\n"

    # Check timeouts on target branch
    if target_timeouts:
        markdown += f"### ⏱️ Timed Out Commands on Target Branch ({args.target_branch})\n\n"
        for cmd in target_timeouts:
            markdown += f"- `{cmd}`: {target_results[cmd].get('error', f'Exceeded {args.timeout}s timeout')}\n"
        markdown += "\n"

    # Check failures on current branch
    if current_failures:
        has_issues = True
        markdown += f"### ❌ Failed Commands on Current Branch ({args.current_branch})\n\n"
        for cmd in current_failures:
            markdown += f"- `{cmd}`: {current_results[cmd].get('error', 'Unknown error')}\n"
        markdown += "\n"

        # Check for new failures on current branch
        new_failures = [
            cmd for cmd in current_failures if cmd not in target_failures
        ]
        if new_failures:
            markdown += "### 🚨 New Failures Introduced\n\n"
            markdown += "The following commands fail on your branch but worked on the target branch:\n\n"
            for cmd in new_failures:
                markdown += f"- `{cmd}`\n"
            markdown += "\n"

    # Check timeouts on current branch
    if current_timeouts:
        has_issues = True
        markdown += f"### ⏱️ Timed Out Commands on Current Branch ({args.current_branch})\n\n"
        for cmd in current_timeouts:
            markdown += f"- `{cmd}`: {current_results[cmd].get('error', f'Exceeded {args.timeout}s timeout')}\n"
        markdown += "\n"

        # Check for new timeouts on current branch
        new_timeouts = [
            cmd
            for cmd in current_timeouts
            if cmd not in target_timeouts and cmd not in target_failures
        ]
        if new_timeouts:
            markdown += "### ⏰ New Timeouts Introduced\n\n"
            markdown += "The following commands time out on your branch but completed on the target branch:\n\n"
            for cmd in new_timeouts:
                markdown += f"- `{cmd}`\n"
            markdown += "\n"

    # Generate comparison table
    markdown += "### Performance Comparison\n\n"
    markdown += f"| Command | {args.target_branch} Time (s) | {args.current_branch} Time (s) | Difference | Status |\n"
    markdown += "|---------|-------------------|-------------------|------------|--------|\n"

    # Track overall performance change
    total_commands = 0
    improved_commands = 0
    degraded_commands = 0
    unchanged_commands = 0
    all_improved = True  # Track if all commands improved or stayed the same

    # Process each command
    all_commands = sorted(
        set(list(target_results.keys()) + list(current_results.keys()))
    )

    for cmd in all_commands:
        # Skip commands that failed or timed out on either branch for timing comparison
        target_status = target_results.get(cmd, {}).get("status", "missing")
        current_status = current_results.get(cmd, {}).get("status", "missing")

        if target_status in ["failed", "timeout"] or current_status in [
            "failed",
            "timeout",
        ]:
            status_str = "⚠️ Issue"

            if cmd in target_results and cmd in current_results:
                if target_status == "failed" and current_status == "failed":
                    status_str = "⚠️ Failed on both branches"
                elif (
                    target_status == "timeout" and current_status == "timeout"
                ):
                    status_str = "⏱️ Timed out on both branches"
                elif target_status == "failed" and current_status == "success":
                    status_str = "✅ Fixed in current branch"
                elif (
                    target_status == "timeout" and current_status == "success"
                ):
                    status_str = "⏱️ → ✅ No longer times out"
                elif target_status == "success" and current_status == "failed":
                    status_str = "❌ Broken in current branch"
                    all_improved = False
                elif (
                    target_status == "success" and current_status == "timeout"
                ):
                    status_str = "⏱️ Now times out"
                    all_improved = False

            target_time_str = (
                "Failed"
                if target_status == "failed"
                else (
                    "Timeout" if target_status == "timeout" else "Not tested"
                )
            )
            current_time_str = (
                "Failed"
                if current_status == "failed"
                else (
                    "Timeout" if current_status == "timeout" else "Not tested"
                )
            )

            markdown += f"| `{cmd}` | {target_time_str} | {current_time_str} | N/A | {status_str} |\n"
            continue

        if cmd in target_results and cmd in current_results:
            total_commands += 1
            target_time = target_results[cmd]["avg_time"]
            current_time = current_results[cmd]["avg_time"]

            # Calculate absolute difference in seconds
            time_diff = target_time - current_time
            abs_diff = abs(time_diff)

            # Format time difference for display
            formatted_diff = format_time_diff(target_time, current_time)

            if (
                time_diff >= args.threshold
            ):  # Current is faster by at least threshold
                status = "✅ Improved"
                improved_commands += 1
            elif (
                time_diff <= -args.threshold
            ):  # Current is slower by at least threshold
                status = "❌ Degraded"
                degraded_commands += 1
                has_issues = True
                all_improved = False
            else:
                status = "✓ No significant change"
                unchanged_commands += 1

            markdown += f"| `{cmd}` | {target_time:.6f} ± {target_results[cmd]['std_dev']:.6f} | {current_time:.6f} ± {current_results[cmd]['std_dev']:.6f} | {formatted_diff} | {status} |\n"
        elif cmd in target_results:
            markdown += f"| `{cmd}` | {target_results[cmd]['avg_time']:.6f} | Not tested | N/A | ❓ Missing |\n"
        elif cmd in current_results:
            markdown += f"| `{cmd}` | Not tested | {current_results[cmd]['avg_time']:.6f} | N/A | ❓ New |\n"

    # Add summary
    if total_commands > 0:
        markdown += "\n### Summary\n\n"
        markdown += f"* Commands tested: {total_commands}\n"
        markdown += f"* Commands improved: {improved_commands} ({improved_commands / total_commands * 100:.1f}%)\n"
        markdown += f"* Commands degraded: {degraded_commands} ({degraded_commands / total_commands * 100:.1f}%)\n"
        markdown += f"* Commands unchanged: {unchanged_commands} ({unchanged_commands / total_commands * 100:.1f}%)\n"

        # Add motivational message if all commands improved or stayed the same
        if all_improved and total_commands > 0 and improved_commands > 0:
            markdown += f"\n### {get_motivational_message()}\n\n"

    # Add metadata
    markdown += "\n### Environment Info\n\n"
    markdown += f"* Target branch: {target_data['metadata']['environment']}\n"
    markdown += (
        f"* Current branch: {current_data['metadata']['environment']}\n"
    )
    markdown += f"* Test timestamp: {target_data['metadata']['timestamp']}\n"
    markdown += f"* Timeout: {target_data['metadata'].get('timeout', args.timeout)} seconds\n"

    # Write results to file
    with open(args.output, "w") as f:
        f.write(markdown)

    # Output if any issues were found (for GitHub Actions)
    print(f"::has_issues::{str(has_issues).lower()}")

    # Print report to stdout
    print(markdown)

    # Exit with appropriate code
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
