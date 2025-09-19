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
    headers = {"Content-Type": "application/json"}
    if auth_key:
        headers["Authorization"] = f"Bearer {auth_key}"

    # Wrap payload in parameters as expected by ZenML deployment API
    deployment_payload = {"parameters": payload}
    print(deployment_payload)

    response = requests.post(
        f"{endpoint_url.rstrip('/')}/invoke",
        data=json.dumps(deployment_payload),
        headers=headers,
        timeout=120,
    )
    print(response.json())
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Document Analysis", page_icon="📄", layout="wide")
st.title("📄 Document Analysis (ZenML Deployed Pipeline)")
st.caption(
    "This app calls a ZenML-deployed pipeline endpoint to analyze documents."
)

with st.sidebar:
    st.header("Configuration")
    default_url = os.getenv("DOCUMENT_ANALYSIS_ENDPOINT", "http://localhost:8001")
    endpoint_url = st.text_input("Endpoint URL", value=default_url)
    auth_key = st.text_input("Auth key (optional)", type="password")
    st.markdown("""
Examples:
- http://localhost:8001
- https://<your-deployment-host>
"""
    )

st.subheader("Input")
tab_content, tab_url, tab_path = st.tabs(["Direct Content", "URL", "Path"])

common_cols = st.columns(3)
with common_cols[0]:
    filename = st.text_input("Filename (optional)", value="document.txt")
with common_cols[1]:
    document_type = st.selectbox(
        "Document Type",
        options=["text", "markdown", "report", "article"],
        index=0,
    )
with common_cols[2]:
    analysis_type = st.selectbox(
        "Analysis Type",
        options=["full", "summary_only"],
        index=0,
    )

request_payload: Optional[Dict[str, Any]] = None

with tab_content:
    content = st.text_area(
        "Content",
        height=220,
        placeholder="Paste your document content here...",
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
                "analysis_type": analysis_type,
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
                "analysis_type": analysis_type,
            }

with tab_path:
    path_value = st.text_input("Path (local or artifact store path)")
    if st.button("Analyze Path"):
        if not path_value.strip():
            st.warning("Please provide a path.")
        else:
            request_payload = {
                "content": None,
                "url": None,
                "path": path_value,
                "filename": filename or "document.txt",
                "document_type": document_type,
                "analysis_type": analysis_type,
            }

if request_payload:
    with st.spinner("Invoking deployment..."):
        try:
            response = post_invoke(endpoint_url, request_payload, auth_key)
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    st.subheader("Raw Response")
    st.code(json.dumps(response, indent=2), language="json")

    outputs = response.get("outputs", {}) if isinstance(response, dict) else {}
    analysis = outputs.get("document_analysis") if isinstance(outputs, dict) else None

    if analysis:
        st.subheader("Analysis Summary")
        met1, met2, met3, met4 = st.columns(4)
        met1.metric("Sentiment", analysis.get("sentiment", "-"))
        met2.metric("Readability", f"{analysis.get('readability_score', 0):.2f}")
        met3.metric("Words", f"{analysis.get('word_count', 0)}")
        met4.metric("Latency (ms)", f"{analysis.get('latency_ms', '-')}")

        st.write("\n")
        st.markdown("**Keywords**")
        st.write(", ".join(analysis.get("keywords", [])))

        st.markdown("**Summary**")
        st.write(analysis.get("summary", "-"))

        st.caption(f"Model: {analysis.get('model', 'N/A')}")
    else:
        st.info("No analysis output found in response. Check the deployment logs.")


