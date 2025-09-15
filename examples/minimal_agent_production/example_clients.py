#!/usr/bin/env python3
"""Example client usage for the document analysis serving endpoint.

This script shows practical examples of how to integrate the document analysis
endpoint into real applications with different input scenarios.
"""

from typing import Any, Dict, Optional

import requests

# Configuration
ENDPOINT_URL = "http://localhost:8001"  # Update with your deployment URL
AUTH_KEY = None  # Set if authentication is enabled


def analyze_direct_content(
    content: str, filename: str = "document.txt"
) -> Dict[str, Any]:
    """Analyze document content directly.

    Use case: When you have text content already in memory.

    Args:
        content: The document content to analyze
        filename: Optional filename for the document

    Returns:
        Analysis results from the API
    """
    payload = {
        "content": content,
        "filename": filename,
        "document_type": "text",
        "analysis_type": "full",
    }

    return _call_api(payload, "Direct Content Analysis")


def analyze_from_url(url: str, document_type: str = "text") -> Dict[str, Any]:
    """Analyze document by downloading from URL.

    Use case: Processing documents from web sources, APIs, or file sharing services.

    Args:
        url: URL to download the document from
        document_type: Type of document (text, markdown, html, etc.)

    Returns:
        Analysis results from the API
    """
    payload = {
        "url": url,
        "document_type": document_type,
        "analysis_type": "full",
    }

    return _call_api(payload, "URL-based Analysis")


def analyze_from_path(
    path: str, document_type: str = "text"
) -> Dict[str, Any]:
    """Analyze document from file path.

    Use case: Processing files from local filesystem or artifact stores.

    Args:
        path: Path to the document file
        document_type: Type of document (text, markdown, etc.)

    Returns:
        Analysis results from the API
    """
    payload = {
        "path": path,
        "document_type": document_type,
        "analysis_type": "full",
    }

    return _call_api(payload, "Path-based Analysis")


def _call_api(payload: Dict[str, Any], operation_name: str) -> Dict[str, Any]:
    """Make API call to the document analysis endpoint."""
    headers = {"Content-Type": "application/json"}
    if AUTH_KEY:
        headers["Authorization"] = f"Bearer {AUTH_KEY}"

    try:
        print(f"🔄 {operation_name}...")

        response = requests.post(
            f"{ENDPOINT_URL}/invoke", json=payload, headers=headers, timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {operation_name} completed successfully")
            return result
        else:
            print(f"❌ {operation_name} failed: {response.status_code}")
            print(f"Error: {response.text}")
            return {}

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {ENDPOINT_URL}")
        print("Make sure the serving endpoint is running!")
        return {}

    except Exception as e:
        print(f"❌ {operation_name} error: {e}")
        return {}


def extract_analysis_data(
    api_response: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Extract analysis data from API response."""
    if (
        "outputs" in api_response
        and "document_analysis" in api_response["outputs"]
    ):
        return api_response["outputs"]["document_analysis"]
    return None


def print_analysis_summary(analysis: Dict[str, Any]) -> None:
    """Print a formatted summary of the analysis results."""
    if not analysis:
        print("No analysis data available")
        return

    print("\n📊 Analysis Summary:")
    print("=" * 50)
    print(f"📝 Summary: {analysis.get('summary', 'N/A')}")
    print(f"🏷️  Keywords: {', '.join(analysis.get('keywords', []))}")
    print(f"😊 Sentiment: {analysis.get('sentiment', 'N/A')}")
    print(f"📚 Word Count: {analysis.get('word_count', 'N/A')}")
    print(f"📖 Readability: {analysis.get('readability_score', 'N/A'):.2f}")
    print(f"🤖 Model: {analysis.get('model', 'N/A')}")
    print(f"⏱️  Latency: {analysis.get('latency_ms', 'N/A')}ms")
    print("=" * 50)


def main():
    """Example usage scenarios for the document analysis API."""
    print("🧪 Document Analysis API - Example Usage")
    print("=" * 60)

    # Example 1: Analyze direct content
    print("\n1️⃣ Example 1: Direct Content Analysis")
    blog_post = """
    # The Future of AI in Healthcare
    
    Artificial Intelligence is revolutionizing healthcare by enabling more accurate 
    diagnoses, personalized treatment plans, and efficient drug discovery processes. 
    Machine learning algorithms can analyze medical images with superhuman accuracy,
    while natural language processing helps extract insights from patient records.
    
    However, challenges remain around data privacy, regulatory approval, and 
    ensuring equitable access to AI-powered healthcare solutions.
    """

    result1 = analyze_direct_content(blog_post, "ai_healthcare_blog.md")
    analysis1 = extract_analysis_data(result1)
    print_analysis_summary(analysis1)

    # Example 2: Analyze from URL
    print("\n2️⃣ Example 2: URL-based Analysis")
    # Using a public markdown file
    result2 = analyze_from_url(
        "https://raw.githubusercontent.com/zenml-io/zenml/main/README.md",
        document_type="markdown",
    )
    analysis2 = extract_analysis_data(result2)
    print_analysis_summary(analysis2)

    # Example 3: Analyze from file path
    print("\n3️⃣ Example 3: Path-based Analysis")
    # This would work if you have a local README.md file
    result3 = analyze_from_path("README.md", document_type="markdown")
    analysis3 = extract_analysis_data(result3)
    print_analysis_summary(analysis3)

    print("\n🎉 All examples completed!")
    print("\n📋 Integration Tips:")
    print("• Use direct content analysis for real-time text processing")
    print("• Use URL analysis for processing documents from web sources")
    print("• Use path analysis for batch processing of stored files")
    print("• Check the 'success' field in responses before processing results")
    print("• Handle network errors and timeouts appropriately")


if __name__ == "__main__":
    main()
