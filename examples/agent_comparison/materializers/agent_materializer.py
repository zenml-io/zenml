"""Custom materializer for BaseAgent objects in ZenML."""

import json
import os
from typing import Any, Dict, Type

from agents import BaseAgent

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class AgentMaterializer(BaseMaterializer):
    """Materializer for BaseAgent objects with visualization capabilities."""

    ASSOCIATED_TYPES = (BaseAgent,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> BaseAgent:
        """Load BaseAgent object from artifact store.

        Args:
            data_type: The type to load (BaseAgent)

        Returns:
            Loaded BaseAgent object
        """
        _ = data_type  # Unused parameter
        with fileio.open(
            os.path.join(self.uri, "agent_metadata.json"), "r"
        ) as f:
            metadata = json.load(f)

        # Note: For this demo, we're not fully serializing/deserializing the agent state
        # In a production system, you'd want to save/restore the full agent configuration
        # For now, we'll create a basic agent instance with the stored name
        agent = BaseAgent(metadata["name"])
        return agent

    def save(self, data: Any) -> None:
        """Save BaseAgent object to artifact store.

        Args:
            data: BaseAgent object to save

        Raises:
            ValueError: If data is not a BaseAgent object
        """
        if not isinstance(data, BaseAgent):
            raise ValueError(
                f"Data must be a BaseAgent object, got {type(data)}"
            )

        # Save basic metadata
        metadata = {
            "name": data.name,
            "type": type(data).__name__,
            "prompt_names": list(data.prompts.keys()) if data.prompts else [],
        }

        with fileio.open(
            os.path.join(self.uri, "agent_metadata.json"), "w"
        ) as f:
            json.dump(metadata, f, indent=2)

        # Save agent architecture description
        if hasattr(data, "get_graph_visualization"):
            with fileio.open(
                os.path.join(self.uri, "architecture_description.txt"), "w"
            ) as f:
                f.write(f"=== {data.name} Architecture ===\n")
                f.write(f"Type: {type(data).__name__}\n")
                f.write("=" * 50 + "\n\n")
                f.write(data.get_graph_visualization())

    def save_visualizations(
        self, data: BaseAgent
    ) -> Dict[str, VisualizationType]:
        """Generate and save visualizations for BaseAgent object.

        Args:
            data: BaseAgent object to visualize

        Returns:
            Dictionary mapping visualization file paths to their types
        """
        visualizations = {}

        # Save Mermaid diagram if available
        if hasattr(data, "get_mermaid_diagram"):
            mermaid_path = os.path.join(self.uri, "architecture_diagram.html")

            # Get the HTML content with Mermaid diagram
            html_content = data.get_mermaid_diagram()

            # Save the visualization
            with fileio.open(mermaid_path, "w") as f:
                f.write(html_content)

            visualizations[mermaid_path] = VisualizationType.HTML

        # Save text visualization if available
        if hasattr(data, "get_graph_visualization"):
            text_path = os.path.join(self.uri, "architecture_text.html")

            # Wrap text visualization in HTML for better display
            text_content = data.get_graph_visualization()
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{data.name} Architecture</title>
    <style>
        body {{ font-family: 'Courier New', monospace; padding: 20px; background-color: #f5f5f5; }}
        .container {{ background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .title {{ color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; margin-bottom: 20px; }}
        .content {{ white-space: pre-wrap; line-height: 1.6; color: #444; }}
        .agent-type {{ background-color: #e8f4f8; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">{data.name} Architecture</h1>
        <div class="agent-type">
            <strong>Agent Type:</strong> {type(data).__name__}
        </div>
        <div class="content">{text_content}</div>
    </div>
</body>
</html>
"""

            with fileio.open(text_path, "w") as f:
                f.write(html_content)

            visualizations[text_path] = VisualizationType.HTML

        return visualizations

    def extract_metadata(self, data: Any) -> Dict[str, Any]:
        """Extract metadata from BaseAgent object.

        Args:
            data: BaseAgent object to extract metadata from

        Returns:
            Metadata dictionary
        """
        metadata = {
            "name": data.name,
            "agent_type": type(data).__name__,
            "has_prompts": bool(data.prompts),
            "prompt_count": len(data.prompts) if data.prompts else 0,
            "prompt_names": list(data.prompts.keys()) if data.prompts else [],
            "has_mermaid_diagram": hasattr(data, "get_mermaid_diagram"),
            "has_text_visualization": hasattr(data, "get_graph_visualization"),
        }

        # Add agent-specific metadata if available
        if hasattr(data, "knowledge_base"):
            metadata["knowledge_base_categories"] = list(
                data.knowledge_base.keys()
            )

        if hasattr(data, "specialists"):
            metadata["specialists"] = list(data.specialists.keys())

        return metadata
