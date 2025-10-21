"""Text Transform Pipeline for ZenML Serving with Run-Only Architecture.

This pipeline demonstrates various text transformations and analysis using
ZenML's millisecond-class serving architecture. It performs multiple text
operations without heavy NLP dependencies - perfect for content processing,
data transformation, or API services.

✅ Zero database writes
✅ Zero filesystem operations
✅ In-memory step output handoff
✅ Per-request parameter injection
✅ Multi-worker safe execution

No permission issues, just pure text processing fun!
"""

import base64
import hashlib
import json
import re
import time
from collections import Counter
from typing import Dict, List, Optional
from urllib.parse import urlparse

from zenml import pipeline, step
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    requirements=[
        "requests",
        "beautifulsoup4",
        "python-dateutil",
    ],
)


@step
def analyze_text_basics(text: str) -> Dict[str, any]:
    """Analyze basic text properties and statistics.

    Args:
        text: Input text to analyze

    Returns:
        Basic text statistics and properties
    """
    # Character analysis
    char_count = len(text)
    char_no_spaces = len(text.replace(" ", ""))
    word_count = len(text.split())
    line_count = len(text.splitlines())

    # Word frequency
    words = re.findall(r"\b\w+\b", text.lower())
    word_freq = Counter(words)
    most_common_words = dict(word_freq.most_common(10))

    # Character types
    uppercase_count = sum(1 for c in text if c.isupper())
    lowercase_count = sum(1 for c in text if c.islower())
    digit_count = sum(1 for c in text if c.isdigit())
    special_char_count = sum(
        1 for c in text if not c.isalnum() and not c.isspace()
    )

    # Patterns
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    phone_pattern = r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}"

    emails = re.findall(email_pattern, text)
    urls = re.findall(url_pattern, text)
    phone_numbers = re.findall(phone_pattern, text)

    # Text complexity (simple heuristic)
    avg_word_length = (
        sum(len(word) for word in words) / len(words) if words else 0
    )
    unique_word_ratio = len(set(words)) / len(words) if words else 0

    return {
        "character_count": char_count,
        "character_count_no_spaces": char_no_spaces,
        "word_count": word_count,
        "line_count": line_count,
        "uppercase_count": uppercase_count,
        "lowercase_count": lowercase_count,
        "digit_count": digit_count,
        "special_char_count": special_char_count,
        "average_word_length": round(avg_word_length, 2),
        "unique_word_ratio": round(unique_word_ratio, 3),
        "most_common_words": most_common_words,
        "emails_found": emails[:5],  # First 5
        "urls_found": urls[:3],  # First 3
        "phone_numbers_found": phone_numbers[:5],  # First 5
        "has_emails": len(emails) > 0,
        "has_urls": len(urls) > 0,
        "has_phone_numbers": len(phone_numbers) > 0,
    }


@step
def transform_text(text: str, transformations: List[str]) -> Dict[str, str]:
    """Apply various text transformations.

    Args:
        text: Input text to transform
        transformations: List of transformations to apply

    Returns:
        Dictionary of transformed text versions
    """
    results = {"original": text}

    # Available transformations
    if "uppercase" in transformations:
        results["uppercase"] = text.upper()

    if "lowercase" in transformations:
        results["lowercase"] = text.lower()

    if "title_case" in transformations:
        results["title_case"] = text.title()

    if "reverse" in transformations:
        results["reverse"] = text[::-1]

    if "remove_spaces" in transformations:
        results["remove_spaces"] = text.replace(" ", "")

    if "remove_punctuation" in transformations:
        import string

        results["remove_punctuation"] = text.translate(
            str.maketrans("", "", string.punctuation)
        )

    if "snake_case" in transformations:
        # Convert to snake_case
        snake = re.sub(r"[^\w\s]", "", text)
        snake = re.sub(r"\s+", "_", snake)
        results["snake_case"] = snake.lower()

    if "camel_case" in transformations:
        # Convert to camelCase
        words = re.findall(r"\b\w+\b", text)
        if words:
            camel = words[0].lower() + "".join(
                w.capitalize() for w in words[1:]
            )
            results["camel_case"] = camel

    if "leetspeak" in transformations:
        # Simple leetspeak conversion
        leet_map = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7"}
        leet = text.lower()
        for char, replacement in leet_map.items():
            leet = leet.replace(char, replacement)
        results["leetspeak"] = leet

    if "base64" in transformations:
        results["base64"] = base64.b64encode(text.encode()).decode()

    if "rot13" in transformations:
        # ROT13 cipher
        rot13 = ""
        for char in text:
            if "a" <= char <= "z":
                rot13 += chr((ord(char) - ord("a") + 13) % 26 + ord("a"))
            elif "A" <= char <= "Z":
                rot13 += chr((ord(char) - ord("A") + 13) % 26 + ord("A"))
            else:
                rot13 += char
        results["rot13"] = rot13

    if "word_reverse" in transformations:
        # Reverse each word but keep order
        results["word_reverse"] = " ".join(word[::-1] for word in text.split())

    if "remove_duplicates" in transformations:
        # Remove duplicate words
        words = text.split()
        seen = set()
        unique_words = []
        for word in words:
            if word.lower() not in seen:
                seen.add(word.lower())
                unique_words.append(word)
        results["remove_duplicates"] = " ".join(unique_words)

    return results


@step
def generate_hashes(text: str) -> Dict[str, str]:
    """Generate various hashes of the text.

    Args:
        text: Input text to hash

    Returns:
        Dictionary of different hash values
    """
    text_bytes = text.encode("utf-8")

    return {
        "md5": hashlib.md5(text_bytes).hexdigest(),
        "sha1": hashlib.sha1(text_bytes).hexdigest(),
        "sha256": hashlib.sha256(text_bytes).hexdigest(),
        "sha512": hashlib.sha512(text_bytes).hexdigest()[
            :64
        ],  # First 64 chars
        "blake2b": hashlib.blake2b(text_bytes).hexdigest()[
            :64
        ],  # First 64 chars
    }


@step
def extract_structured_data(text: str) -> Dict[str, any]:
    """Extract structured data from text.

    Args:
        text: Input text to analyze

    Returns:
        Extracted structured data
    """
    results = {}

    # Try to parse as JSON
    try:
        json_data = json.loads(text)
        results["is_valid_json"] = True
        results["json_type"] = type(json_data).__name__
        if isinstance(json_data, dict):
            results["json_keys"] = list(json_data.keys())[:10]  # First 10 keys
        elif isinstance(json_data, list):
            results["json_length"] = len(json_data)
    except:
        results["is_valid_json"] = False

    # Extract key-value pairs (simple format: key=value or key:value)
    kv_pattern = r"(\w+)\s*[=:]\s*([^\s,;]+)"
    key_values = re.findall(kv_pattern, text)
    if key_values:
        results["extracted_key_values"] = dict(key_values[:10])  # First 10

    # Extract quoted strings
    quoted_pattern = r'"([^"]*)"'
    quoted_strings = re.findall(quoted_pattern, text)
    results["quoted_strings"] = quoted_strings[:5]  # First 5

    # Extract numbers
    number_pattern = r"-?\d+\.?\d*"
    numbers = re.findall(number_pattern, text)
    if numbers:
        float_numbers = [float(n) for n in numbers[:20]]  # First 20
        results["numbers_found"] = float_numbers
        results["numbers_sum"] = sum(float_numbers)
        results["numbers_avg"] = sum(float_numbers) / len(float_numbers)
        results["numbers_min"] = min(float_numbers)
        results["numbers_max"] = max(float_numbers)

    # Extract hashtags
    hashtag_pattern = r"#\w+"
    hashtags = re.findall(hashtag_pattern, text)
    results["hashtags"] = hashtags[:10]  # First 10

    # Extract mentions
    mention_pattern = r"@\w+"
    mentions = re.findall(mention_pattern, text)
    results["mentions"] = mentions[:10]  # First 10

    # Extract dates (simple patterns)
    date_patterns = [
        r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        r"\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
        r"\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY
    ]
    dates_found = []
    for pattern in date_patterns:
        dates_found.extend(re.findall(pattern, text))
    results["dates_found"] = dates_found[:5]  # First 5

    return results


@step
def create_summary(
    text: str,
    basics: Dict[str, any],
    transformations: Dict[str, str],
    hashes: Dict[str, str],
    structured_data: Dict[str, any],
) -> Dict[str, any]:
    """Create a comprehensive summary of all analyses.

    Args:
        text: Original text
        basics: Basic text analysis results
        transformations: Text transformation results
        hashes: Hash values
        structured_data: Extracted structured data

    Returns:
        Complete analysis summary
    """
    # Create text preview
    preview_length = 100
    if len(text) > preview_length:
        preview = text[:preview_length] + "..."
    else:
        preview = text

    # Determine content type
    if basics["has_urls"]:
        content_type = "url-content"
    elif basics["has_emails"]:
        content_type = "contact-info"
    elif structured_data.get("is_valid_json"):
        content_type = "json-data"
    elif len(structured_data.get("hashtags", [])) > 2:
        content_type = "social-media"
    elif basics["word_count"] < 10:
        content_type = "short-text"
    else:
        content_type = "general-text"

    # Calculate text entropy (simple Shannon entropy)
    char_freq = Counter(text)
    total_chars = len(text)
    entropy = 0
    if total_chars > 0:
        for count in char_freq.values():
            probability = count / total_chars
            if probability > 0:
                import math

                entropy -= probability * math.log2(probability)

    return {
        "preview": preview,
        "content_type": content_type,
        "processing_timestamp": time.time(),
        "entropy": round(entropy, 3),
        "summary_stats": {
            "total_characters": basics["character_count"],
            "total_words": basics["word_count"],
            "unique_word_ratio": basics["unique_word_ratio"],
            "has_structured_data": bool(
                structured_data.get("extracted_key_values")
            )
            or structured_data.get("is_valid_json", False),
        },
        "transformations_applied": len(transformations) - 1,  # Minus original
        "hash_fingerprint": hashes["sha256"][:16],  # Short fingerprint
        "detailed_results": {
            "basics": basics,
            "transformations": transformations,
            "hashes": hashes,
            "structured_data": structured_data,
        },
    }


@step
def fetch_url_content(url: Optional[str]) -> Dict[str, any]:
    """Fetch and extract content from a URL if provided.

    Args:
        url: Optional URL to fetch

    Returns:
        Extracted content or empty result
    """
    if not url:
        return {"url_provided": False}

    try:
        import requests
        from bs4 import BeautifulSoup

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"url_provided": True, "error": "Invalid URL format"}

        # Fetch content
        response = requests.get(
            url,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ZenML/1.0)"},
        )
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract text
        text = soup.get_text(separator=" ", strip=True)

        # Extract metadata
        title = soup.find("title")
        title_text = title.text if title else "No title"

        # Extract links
        links = [a.get("href", "") for a in soup.find_all("a", href=True)]

        return {
            "url_provided": True,
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "title": title_text,
            "text_preview": text[:500] + "..." if len(text) > 500 else text,
            "text_length": len(text),
            "links_found": len(links),
            "sample_links": links[:5],  # First 5 links
        }

    except requests.RequestException as e:
        return {
            "url_provided": True,
            "success": False,
            "url": url,
            "error": str(e),
        }
    except Exception as e:
        return {
            "url_provided": True,
            "success": False,
            "url": url,
            "error": f"Unexpected error: {str(e)}",
        }


@pipeline(settings={"docker": docker_settings})
def text_transform_pipeline(
    text: str = "Hello World! This is a test message with email@example.com",
    transformations: List[str] = [
        "uppercase",
        "lowercase",
        "reverse",
        "base64",
    ],
    fetch_url: Optional[str] = None,
) -> Dict[str, any]:
    """Text transformation and analysis pipeline optimized for serving.

    This pipeline performs comprehensive text analysis and transformations:
    - Basic text statistics and pattern detection
    - Multiple text transformations (case, encoding, etc.)
    - Hash generation for fingerprinting
    - Structured data extraction
    - Optional URL content fetching

    Perfect for content processing, data transformation, or text APIs.

    Args:
        text: Text to analyze and transform
        transformations: List of transformations to apply
        fetch_url: Optional URL to fetch and analyze

    Returns:
        Comprehensive analysis and transformation results
    """
    # Analyze text
    basics = analyze_text_basics(text)
    transformed = transform_text(text, transformations)
    hashes = generate_hashes(text)
    structured = extract_structured_data(text)

    # Optional URL fetching
    url_content = fetch_url_content(fetch_url)

    # Generate summary
    summary = create_summary(text, basics, transformed, hashes, structured)

    # The URL content will be handled inside the create_final_summary step
    return combine_results(summary, url_content)


@step
def combine_results(
    summary: Dict[str, any], url_content: Dict[str, any]
) -> Dict[str, any]:
    """Combine the main summary with optional URL analysis.

    Args:
        summary: Main text analysis summary
        url_content: URL fetch results

    Returns:
        Combined results
    """
    # Add URL content if fetched
    if url_content.get("success") and url_content.get("text_preview"):
        # Also analyze the fetched content
        url_text = url_content["text_preview"]
        # Create basic analysis of URL content
        url_basics = {
            "text_length": len(url_text),
            "word_count": len(url_text.split()),
            "title": url_content.get("title", ""),
            "links_found": url_content.get("links_found", 0),
        }
        summary["url_analysis"] = {
            "url_content": url_content,
            "url_text_stats": url_basics,
        }
    elif url_content.get("url_provided"):
        summary["url_analysis"] = url_content

    return summary


if __name__ == "__main__":
    print("🔄 Creating Text Transform Pipeline Deployment...\n")

    print("✨ This pipeline transforms and analyzes text with:")
    print("   - Pattern detection (emails, URLs, phones)")
    print("   - Text transformations (case, encoding, cipher)")
    print("   - Hash generation (MD5, SHA, Blake2b)")
    print("   - Structured data extraction")
    print("   - Optional URL content fetching\n")

    try:
        # Create deployment
        text_transform_pipeline._prepare_if_possible()
        deployment = text_transform_pipeline._create_deployment()

        print(f"✅ Deployment ID: {deployment.id}")
        print("\n🚀 Start serving with millisecond latency:")
        print(f"export ZENML_PIPELINE_DEPLOYMENT_ID={deployment.id}")
        print("python -m zenml.deployers.serving.app")

        print("\n📝 Example requests:")
        print("\n# Basic text analysis")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"text": "Hello World! Contact us at info@zenml.io"}}\''
        )

        print("\n# Apply multiple transformations")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"text": "Transform This Text!", "transformations": ["uppercase", "reverse", "leetspeak", "base64"]}}\''
        )

        print("\n# Extract structured data")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"text": "user=john age=25 score=98.5 #ml #zenml @zenml_io"}}\''
        )

        print("\n# Analyze JSON data")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"text": "{\\"name\\": \\"ZenML\\", \\"version\\": \\"0.84.3\\", \\"features\\": [\\"pipelines\\", \\"serving\\"]}"}}\''
        )

        print("\n# Fetch and analyze URL content")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"text": "Analyze this", "fetch_url": "https://example.com"}}\''
        )

        print("\n# Stream real-time transformations")
        print("wscat -c ws://localhost:8000/stream")
        print(
            '# Send: {"parameters": {"text": "Your text here...", "transformations": ["uppercase", "rot13"]}}'
        )

        print("\n⚡ No permission issues! Just pure text processing fun!")

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        print("💡 Make sure you have ZenML installed and configured")
