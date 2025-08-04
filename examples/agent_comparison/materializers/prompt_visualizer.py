"""Prompt visualizer for generating HTML visualizations of prompts."""

import html
from typing import Any, List

from materializers.prompt import Prompt
from zenml.types import HTMLString


def visualize_prompt(prompt: Prompt) -> HTMLString:
    """Generate HTML visualization for a single prompt.

    Args:
        prompt: The Prompt object to visualize

    Returns:
        HTML string containing the visualization
    """
    variables_html = ""
    if prompt.get_variable_names():
        variables_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">📝 Variables</h3>
            <div class="variables-list">
                {" ".join([f"<code>{var}</code>" for var in prompt.get_variable_names()])}
            </div>
        </div>
        """

    tags_html = ""
    if prompt.tags:
        tags_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">🏷️ Tags</h3>
            <div class="tags-list">
                {" ".join([f'<span class="dr-badge dr-badge--info">{k}: {v}</span>' for k, v in prompt.tags.items()])}
            </div>
        </div>
        """

    description_html = ""
    if prompt.description:
        description_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">📋 Description</h3>
            <p style="color: var(--color-text-secondary); line-height: 1.6;">{html.escape(prompt.description)}</p>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prompt: {prompt.name}</title>
        <style>
            /* ZenML Design System CSS Variables */
            :root {{
                --color-primary: #7a3ef4;
                --color-primary-dark: #6b35db;
                --color-primary-light: #9d6ff7;
                --color-secondary: #667eea;
                --color-success: #179f3e;
                --color-success-light: #d4edda;
                --color-success-dark: #155724;
                --color-warning: #a65d07;
                --color-warning-light: #fff3cd;
                --color-info: #007bff;
                --color-text-primary: #333;
                --color-text-secondary: #666;
                --color-text-muted: #999;
                --color-heading: #2c3e50;
                --color-bg-primary: #f5f7fa;
                --color-bg-secondary: #f8f9fa;
                --color-bg-white: #ffffff;
                --color-border: #e9ecef;
                --color-border-light: #dee2e6;
                --font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                --font-family-mono: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
                --spacing-xs: 4px;
                --spacing-sm: 8px;
                --spacing-md: 16px;
                --spacing-lg: 24px;
                --spacing-xl: 32px;
                --radius-sm: 4px;
                --radius-md: 6px;
                --radius-lg: 8px;
                --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
                --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
                --shadow-hover: 0 6px 16px rgba(0, 0, 0, 0.1);
                --transition-base: all 0.3s ease;
            }}
            
            body {{
                font-family: var(--font-family-base);
                font-size: 14px;
                line-height: 1.6;
                color: var(--color-text-primary);
                background-color: var(--color-bg-primary);
                margin: 0;
                padding: var(--spacing-md);
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }}
            
            .dr-container {{
                max-width: 900px;
                margin: 0 auto;
                padding: var(--spacing-md);
            }}
            
            .dr-card {{
                background: var(--color-bg-white);
                border-radius: var(--radius-md);
                padding: var(--spacing-lg);
                box-shadow: var(--shadow-md);
                margin-bottom: var(--spacing-lg);
                transition: var(--transition-base);
                border: 1px solid var(--color-border-light);
            }}
            
            .dr-h1 {{
                color: var(--color-heading);
                font-size: 2em;
                font-weight: 500;
                margin: 0 0 var(--spacing-lg) 0;
                padding-bottom: var(--spacing-sm);
                border-bottom: 2px solid var(--color-primary);
            }}
            
            .dr-grid--stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: var(--spacing-md);
            }}
            
            .dr-stat-card {{
                background: var(--color-bg-white);
                border-radius: var(--radius-md);
                padding: var(--spacing-lg);
                text-align: center;
                transition: var(--transition-base);
                border: 1px solid var(--color-border);
                box-shadow: var(--shadow-sm);
            }}
            
            .dr-stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: var(--shadow-hover);
            }}
            
            .dr-stat-value {{
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--color-primary);
                margin-bottom: var(--spacing-xs);
                display: block;
            }}
            
            .dr-stat-label {{
                color: var(--color-text-secondary);
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                display: block;
                font-weight: 500;
            }}
            
            .dr-badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                line-height: 1.5;
                margin: 2px;
            }}
            
            .dr-badge--primary {{
                background-color: var(--color-primary);
                color: white;
            }}
            
            .dr-badge--info {{
                background-color: #e1f5fe;
                color: #0277bd;
            }}
            
            .dr-section {{
                background: var(--color-bg-white);
                border-radius: var(--radius-md);
                padding: var(--spacing-lg);
                margin-bottom: var(--spacing-lg);
                box-shadow: var(--shadow-sm);
                border: 1px solid var(--color-border-light);
            }}
            
            .dr-section--bordered {{
                border-left: 3px solid var(--color-primary);
            }}
            
            .dr-code {{
                background-color: var(--color-heading);
                color: #ecf0f1;
                border: 1px solid var(--color-border);
                border-radius: var(--radius-md);
                padding: var(--spacing-lg);
                font-family: var(--font-family-mono);
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.5;
                margin: var(--spacing-md) 0;
            }}
            
            .dr-h3 {{
                color: var(--color-primary);
                font-size: 1.2em;
                font-weight: 500;
                margin-top: var(--spacing-md);
                margin-bottom: var(--spacing-sm);
            }}
            
            .prompt-version {{
                color: var(--color-text-muted);
                font-size: 14px;
                margin-top: var(--spacing-xs);
            }}
            
            .variables-list {{
                margin: var(--spacing-sm) 0;
            }}
            
            .variables-list code {{
                background: #e8f4f8;
                padding: 4px 8px;
                border-radius: var(--radius-sm);
                font-family: var(--font-family-mono);
                color: var(--color-primary);
                font-size: 13px;
                margin: 2px;
            }}
            
            .tags-list {{
                margin: var(--spacing-sm) 0;
            }}
            
            @media (max-width: 768px) {{
                .dr-grid--stats {{
                    grid-template-columns: 1fr;
                }}
                
                .dr-h1 {{
                    font-size: 1.5em;
                }}
                
                .dr-stat-value {{
                    font-size: 1.25rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="dr-container">
            <div class="dr-card">
                <h1 class="dr-h1">🎯 {html.escape(prompt.name)}</h1>
                <div class="prompt-version">Version: {html.escape(prompt.version)} <span class="dr-badge dr-badge--primary">Prompt</span></div>
            </div>
            
            <div class="dr-grid dr-grid--stats">
                <div class="dr-stat-card">
                    <span class="dr-stat-value">📅</span>
                    <span class="dr-stat-label">Created</span>
                    <div style="color: var(--color-text-secondary); margin-top: 8px; font-size: 13px;">
                        {prompt.created_at.strftime("%Y-%m-%d %H:%M:%S")}
                    </div>
                </div>
                <div class="dr-stat-card">
                    <span class="dr-stat-value">👤</span>
                    <span class="dr-stat-label">Author</span>
                    <div style="color: var(--color-text-secondary); margin-top: 8px; font-size: 13px;">
                        {html.escape(prompt.author or "Unknown")}
                    </div>
                </div>
                <div class="dr-stat-card">
                    <span class="dr-stat-value">{len(prompt.content):,}</span>
                    <span class="dr-stat-label">Characters</span>
                </div>
                <div class="dr-stat-card">
                    <span class="dr-stat-value">{len(prompt.get_variable_names())}</span>
                    <span class="dr-stat-label">Variables</span>
                </div>
            </div>
            
            {description_html}
            {variables_html}
            {tags_html}
            
            <div class="dr-section dr-section--bordered">
                <h3 class="dr-h3">💬 Prompt Content</h3>
                <div class="dr-code">{html.escape(prompt.content)}</div>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLString(html_content)


def visualize_prompts(prompts: List[Prompt]) -> HTMLString:
    """Generate HTML visualization for multiple prompts.

    Args:
        prompts: List of Prompt objects to visualize

    Returns:
        HTML string containing the visualization
    """
    prompts_html = ""
    for i, prompt in enumerate(prompts):
        variables_count = len(prompt.get_variable_names())
        variables_text = (
            f"{variables_count} variables: {', '.join(prompt.get_variable_names())}"
            if variables_count > 0
            else "No variables"
        )

        prompts_html += f"""
        <div class="prompt-card">
            <div class="prompt-card-header">
                <h3>🎯 {html.escape(prompt.name)}</h3>
                <span class="version-badge">v{html.escape(prompt.version)}</span>
            </div>
            <div class="prompt-card-meta">
                <div class="meta-item">
                    <strong>📋 Description:</strong> {html.escape(prompt.description or "No description")}
                </div>
                <div class="meta-item">
                    <strong>🔧 Variables:</strong> {variables_text}
                </div>
                <div class="meta-item">
                    <strong>📏 Length:</strong> {len(prompt.content):,} characters
                </div>
                <div class="meta-item">
                    <strong>📅 Created:</strong> {prompt.created_at.strftime("%Y-%m-%d %H:%M:%S")}
                </div>
            </div>
            <div class="prompt-preview">
                <strong>💬 Preview:</strong>
                <div class="content-preview">{html.escape(prompt.content[:200])}{"..." if len(prompt.content) > 200 else ""}</div>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prompt Collection</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            .prompts-container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
            }}
            .header .subtitle {{
                color: #7f8c8d;
                margin-top: 5px;
            }}
            .prompt-card {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                border-left: 4px solid #3498db;
            }}
            .prompt-card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 10px;
            }}
            .prompt-card-header h3 {{
                margin: 0;
                color: #2c3e50;
            }}
            .version-badge {{
                background: #3498db;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            .prompt-card-meta {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 10px;
                margin-bottom: 15px;
            }}
            .meta-item {{
                color: #34495e;
                font-size: 14px;
            }}
            .prompt-preview {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 3px solid #3498db;
            }}
            .content-preview {{
                font-family: 'Courier New', monospace;
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                border-radius: 3px;
                margin-top: 5px;
                font-size: 12px;
                line-height: 1.4;
            }}
        </style>
    </head>
    <body>
        <div class="prompts-container">
            <div class="header">
                <h1>📚 Prompt Collection</h1>
                <div class="subtitle">{len(prompts)} prompts loaded as ZenML artifacts</div>
            </div>
            
            {prompts_html}
        </div>
    </body>
    </html>
    """

    return HTMLString(html_content)


def visualize_prompt_data(data: Any) -> HTMLString:
    """Generate HTML visualization for prompt data.

    Args:
        data: Prompt object or list of Prompt objects

    Returns:
        HTML string containing the visualization
    """
    # Use duck typing to check if it's a single prompt object
    if (
        hasattr(data, "name")
        and hasattr(data, "content")
        and hasattr(data, "version")
    ):
        return visualize_prompt(data)
    elif isinstance(data, list) and all(
        hasattr(item, "name")
        and hasattr(item, "content")
        and hasattr(item, "version")
        for item in data
    ):
        return visualize_prompts(data)
    else:
        return HTMLString(
            f"<p>Invalid prompt data format: {type(data)} - {data}</p>"
        )
