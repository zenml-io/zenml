#!/usr/bin/env python3
"""
🚀 ZenML Prompt Management Demo Launcher

This is your one-stop demo launcher for experiencing ZenML's 
comprehensive prompt management capabilities.

Quick Start:
    python demo.py                    # Interactive demo selection
    python demo.py --quick            # Quick showcase demo
    python demo.py --full             # Complete demonstration
    python demo.py --help             # Show all options
"""

import click
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from run_comprehensive import main as run_comprehensive_main
except ImportError:
    print("❌ Error: Could not import comprehensive demo")
    print("Make sure you're in the prompt_example directory")
    sys.exit(1)


def print_banner():
    """Print welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════════╗
║                     🚀 ZenML PROMPT MANAGEMENT SHOWCASE 🚀                       ║
║                                                                                  ║
║              The Ultimate LLMOps Platform - See Why ZenML Wins                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  🎯 WHAT YOU'LL SEE:                                                            ║
║    • Complete prompt lifecycle management                                       ║
║    • LLM-as-Judge automated evaluation                                         ║
║    • Real-time A/B testing with statistical analysis                           ║
║    • Production deployment with monitoring                                     ║
║    • Multi-provider LLM integration (OpenAI, Anthropic, etc.)                 ║
║    • Advanced analytics and optimization                                       ║
║                                                                                  ║
║  🏆 WHY ZENML BEATS THE COMPETITION:                                            ║
║    ✅ vs LangSmith: Full MLOps integration, not just monitoring               ║
║    ✅ vs PromptLayer: Production deployment, not just logging                 ║
║    ✅ vs W&B: LLM-optimized workflows, not generic tracking                   ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_setup():
    """Check if ZenML is properly set up."""
    try:
        from zenml.client import Client
        client = Client()
        print(f"✅ ZenML connected - Active stack: {client.active_stack.name}")
        return True
    except Exception as e:
        print(f"❌ ZenML setup issue: {e}")
        print("\n🔧 Quick fix:")
        print("   zenml init")
        print("   zenml up")
        return False


def check_api_keys():
    """Check for LLM API keys."""
    api_keys = {
        "OpenAI": os.getenv("OPENAI_API_KEY"),
        "Anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "LiteLLM": os.getenv("LITELLM_API_KEY")
    }
    
    available_keys = [name for name, key in api_keys.items() if key]
    
    if available_keys:
        print(f"✅ API keys found: {', '.join(available_keys)}")
        return True
    else:
        print("⚠️  No LLM API keys found")
        print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY for real LLM calls")
        print("   Demo will run with realistic mock responses")
        return False


@click.command()
@click.option(
    "--quick", 
    is_flag=True, 
    help="Run quick showcase demo (5 minutes)"
)
@click.option(
    "--full", 
    is_flag=True, 
    help="Run complete demonstration (15 minutes)"
)
@click.option(
    "--interactive",
    is_flag=True,
    default=True,
    help="Interactive demo selection (default)"
)
@click.option(
    "--use-mock",
    is_flag=True,
    help="Force mock LLM responses (faster demo)"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable pipeline caching"
)
def main(quick: bool, full: bool, interactive: bool, use_mock: bool, no_cache: bool):
    """Launch ZenML Prompt Management Demo."""
    
    print_banner()
    
    # Setup checks
    if not check_setup():
        return
    
    has_api_keys = check_api_keys()
    
    # Determine demo mode
    if quick:
        demo_mode = "showcase"
        print("\n🚀 Starting Quick Showcase Demo...")
        print("   Duration: ~5 minutes")
        print("   Features: Prompt creation, evaluation, comparison")
        
    elif full:
        demo_mode = "all"
        print("\n🏁 Starting Complete Demonstration...")
        print("   Duration: ~15 minutes") 
        print("   Features: All capabilities including production deployment")
        
    else:
        # Interactive mode
        print("\n🎮 Choose your demo experience:")
        print("   1. 🚀 Quick Showcase (5 min) - Core features")
        print("   2. 🔬 Optimization Demo (8 min) - Iterative improvement")
        print("   3. 🏭 Production Demo (10 min) - Enterprise deployment")
        print("   4. 🏁 Complete Demo (15 min) - Everything!")
        print("   5. ❌ Exit")
        
        while True:
            choice = click.prompt("Select option", type=int, default=1)
            
            if choice == 1:
                demo_mode = "showcase"
                break
            elif choice == 2:
                demo_mode = "optimization"
                break
            elif choice == 3:
                demo_mode = "production"
                break
            elif choice == 4:
                demo_mode = "all"
                break
            elif choice == 5:
                print("👋 Thanks for trying ZenML!")
                return
            else:
                print("❌ Invalid choice. Please select 1-5.")
    
    # Auto-enable mock if no API keys and not explicitly set
    if not has_api_keys and not use_mock:
        use_mock = True
        print("🎭 Enabling mock mode - no API keys detected")
    
    print(f"\n⚙️  Configuration:")
    print(f"   Demo mode: {demo_mode}")
    print(f"   Mock responses: {'enabled' if use_mock else 'disabled'}")
    print(f"   Cache: {'disabled' if no_cache else 'enabled'}")
    
    if not use_mock:
        print("💰 Note: Real LLM calls will incur API costs (~$0.10-0.50)")
        if not click.confirm("Continue with real API calls?"):
            use_mock = True
            print("🎭 Switched to mock mode")
    
    print("\n" + "="*80)
    print("🎬 STARTING DEMO...")
    print("="*80)
    
    # Import and run the comprehensive demo
    try:
        # Create a click context for the comprehensive runner
        from click.testing import CliRunner
        runner = CliRunner()
        
        args = ["--demo", demo_mode]
        if no_cache:
            args.append("--no-cache")
        if use_mock:
            args.append("--use-mock")
        
        # Run the comprehensive demo
        result = runner.invoke(run_comprehensive_main, args, catch_exceptions=False)
        
        if result.exit_code == 0:
            print("\n" + "="*80)
            print("🎉 DEMO COMPLETED SUCCESSFULLY!")
            print("="*80)
            
            print("\n📊 What to explore next:")
            print("   1. 🌐 ZenML Dashboard - Rich visualizations and artifact lineage")
            print("   2. 📈 Pipeline Runs - Compare different experiments")
            print("   3. 🔍 Artifact Details - Inspect prompt versions and metadata")
            print("   4. 📋 Model Registry - See deployed prompt versions")
            
            print("\n🚀 Take action:")
            print("   • Customize prompts for your use case")
            print("   • Add your own evaluation criteria")
            print("   • Connect to your infrastructure stack")
            print("   • Deploy to your production environment")
            
            print("\n💡 Learn more:")
            print("   • Documentation: https://docs.zenml.io")
            print("   • Examples: See other examples/ directories")
            print("   • Community: Join our Slack community")
            
        else:
            print("\n❌ Demo encountered an error")
            print("Check the output above for details")
            
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure ZenML server is running: 'zenml status'")
        print("   2. Check dependencies: 'pip install -r requirements.txt'") 
        print("   3. Try mock mode: python demo.py --use-mock")
        print("   4. Check logs in ZenML dashboard")


if __name__ == "__main__":
    main()