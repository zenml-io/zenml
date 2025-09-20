#!/usr/bin/env python3
"""Simple Streamlit frontend for the deployed document analysis endpoint.

This UI submits requests to a ZenML-deployed pipeline endpoint. It avoids
browser CORS issues by running server-side. Configure the endpoint URL in the
sidebar.
"""

import json
import os
from typing import Any, Dict, Optional

import requests
import streamlit as st


def post_invoke(
    endpoint_url: str,
    payload: Dict[str, Any],
    auth_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a POST request to the ZenML pipeline deployment endpoint.

    Args:
        endpoint_url: The deployment endpoint URL
        payload: The request payload containing pipeline parameters
        auth_key: Optional authentication key for the endpoint

    Returns:
        Dict containing the pipeline execution response
    """
    headers = {"Content-Type": "application/json"}
    if auth_key:
        headers["Authorization"] = f"Bearer {auth_key}"

    # Wrap payload in parameters as expected by ZenML deployment API
    deployment_payload = {"parameters": payload}

    response = requests.post(
        f"{endpoint_url.rstrip('/')}/invoke",
        data=json.dumps(deployment_payload),
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    result: Dict[str, Any] = response.json()
    return result


st.set_page_config(
    page_title="Document Analysis", page_icon="📄", layout="wide"
)
st.title("📄 Document Analysis (ZenML Deployed Pipeline)")
st.caption(
    "This app calls a ZenML-deployed pipeline endpoint to analyze documents."
)

with st.sidebar:
    st.header("Configuration")
    default_url = os.getenv(
        "DOCUMENT_ANALYSIS_ENDPOINT", "http://localhost:8000"
    )
    endpoint_url = st.text_input("Endpoint URL", value=default_url)
    auth_key = st.text_input("Auth key (optional)", type="password")
    st.markdown("""
Examples:
- http://localhost:8000
- https://<your-deployment-host>
""")

st.subheader("Input")
tab_content, tab_upload, tab_url = st.tabs(
    ["✏️ Direct Content", "📁 Upload File", "🌐 URL"]
)

common_cols = st.columns(2)
with common_cols[0]:
    filename = st.text_input("Filename (optional)", value="document.txt")
with common_cols[1]:
    document_type = st.selectbox(
        "Document Type",
        options=["text", "markdown", "report", "article"],
        index=0,
    )

request_payload: Optional[Dict[str, Any]] = None

with tab_upload:
    st.markdown("**Upload a document file for analysis**")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "md", "csv", "json", "py", "js", "html", "xml"],
        help="Upload text files, markdown, code files, or other text-based documents",
    )

    if uploaded_file is not None:
        # Read file content
        content = uploaded_file.read().decode("utf-8")
        file_extension = uploaded_file.name.split(".")[-1].lower()

        # Auto-detect document type based on file extension
        extension_to_type = {
            "md": "markdown",
            "txt": "text",
            "py": "text",
            "js": "text",
            "html": "text",
            "xml": "text",
            "csv": "text",
            "json": "text",
        }
        auto_doc_type = extension_to_type.get(file_extension, "text")

        st.success(
            f"✅ File uploaded: {uploaded_file.name} ({len(content)} characters)"
        )
        st.info(f"🔍 Auto-detected document type: **{auto_doc_type}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Analyze Uploaded File", type="primary"):
                request_payload = {
                    "content": content,
                    "url": None,
                    "path": None,
                    "filename": uploaded_file.name,
                    "document_type": auto_doc_type,
                }

        with col2:
            with st.expander("📄 Preview content"):
                st.text_area(
                    "File content preview",
                    content[:1000] + "..." if len(content) > 1000 else content,
                    height=200,
                    disabled=True,
                )

with tab_content:
    example_text = """Machine learning is revolutionizing industries across the globe. From healthcare to finance, artificial intelligence systems are processing vast amounts of data to uncover patterns and insights that were previously impossible to detect.

These advanced algorithms can analyze medical images to assist doctors in diagnosis, predict market trends to help investors make informed decisions, and even optimize supply chains to reduce costs and improve efficiency.

The future of AI looks promising, with new breakthroughs happening regularly. As we continue to develop more sophisticated models and techniques, we can expect to see even more transformative applications that will benefit society as a whole."""

    content = st.text_area(
        "Content",
        value=example_text,
        height=220,
        help="Edit this example text or paste your own content",
    )
    if st.button("Analyze Content", type="primary"):
        if not content.strip():
            st.warning("Please provide content.")
        else:
            request_payload = {
                "content": content,
                "url": None,
                "path": None,
                "filename": filename or "document.txt",
                "document_type": document_type,
            }

with tab_url:
    url_value = st.text_input("Document URL", placeholder="https://...")
    if st.button("Analyze URL"):
        if not url_value.strip():
            st.warning("Please provide a URL.")
        else:
            request_payload = {
                "content": None,
                "url": url_value,
                "path": None,
                "filename": filename or "document.txt",
                "document_type": document_type,
            }


if request_payload:
    with st.spinner("🔄 Analyzing document..."):
        try:
            response = post_invoke(endpoint_url, request_payload, auth_key)
        except Exception as e:
            st.error(f"❌ Request failed: {e}")
            st.stop()

    # Extract analysis data
    outputs = response.get("outputs", {}) if isinstance(response, dict) else {}
    analysis_key = (
        next((k for k in outputs.keys() if "document_analysis" in k), None)
        if isinstance(outputs, dict)
        else None
    )
    analysis = outputs.get(analysis_key) if analysis_key else None

    if analysis:
        st.success("✅ Analysis completed!")

        # Main results in a nice container
        with st.container():
            st.subheader("📊 Analysis Results")

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sentiment_emoji = {
                    "positive": "😊",
                    "negative": "😞",
                    "neutral": "😐",
                }.get(analysis.get("sentiment", "neutral"), "😐")
                st.metric(
                    "Sentiment",
                    f"{sentiment_emoji} {analysis.get('sentiment', 'N/A').title()}",
                )
            with col2:
                readability = analysis.get("readability_score", 0)
                readability_label = (
                    "Easy"
                    if readability > 0.7
                    else "Medium"
                    if readability > 0.4
                    else "Hard"
                )
                st.metric(
                    "Readability", f"{readability:.2f} ({readability_label})"
                )
            with col3:
                st.metric("Word Count", f"{analysis.get('word_count', 0):,}")
            with col4:
                st.metric(
                    "Processing Time", f"{analysis.get('latency_ms', 0)} ms"
                )

            # Analysis type indicator
            analysis_method = analysis.get("metadata", {}).get(
                "analysis_method", "unknown"
            )
            if analysis_method == "llm":
                st.info("🤖 Powered by AI (OpenAI GPT-4o-mini)")
            else:
                st.info("⚙️ Deterministic analysis (offline mode)")

        # Summary section
        with st.container():
            st.subheader("📝 Summary")
            st.markdown(f"*{analysis.get('summary', 'No summary available')}*")

        # Keywords section
        with st.container():
            st.subheader("🔑 Keywords")
            keywords = analysis.get("keywords", [])
            if keywords:
                # Display keywords in columns for better layout
                keyword_cols = st.columns(min(len(keywords), 3))
                for i, keyword in enumerate(keywords):
                    with keyword_cols[i % 3]:
                        st.markdown(f"🏷️ **{keyword}**")
            else:
                st.write("No keywords extracted")

        # Document info
        with st.expander("📄 Document Details"):
            doc_info = analysis.get("document", {})
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Filename:** {doc_info.get('filename', 'N/A')}")
                st.write(
                    f"**Document Type:** {doc_info.get('document_type', 'N/A')}"
                )
            with col2:
                st.write(
                    f"**Analysis Type:** {doc_info.get('analysis_type', 'N/A')}"
                )
                st.write(f"**Model:** {analysis.get('model', 'N/A')}")

        # Raw response in expandable section
        with st.expander("🔍 Raw API Response"):
            st.code(json.dumps(response, indent=2), language="json")

    else:
        st.error(
            "❌ No analysis output found in response. Check the deployment logs."
        )
        with st.expander("🔍 Raw Response for Debugging"):
            st.code(json.dumps(response, indent=2), language="json")
