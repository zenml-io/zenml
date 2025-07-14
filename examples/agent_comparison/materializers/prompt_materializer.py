"""Custom materializer for Prompt objects in ZenML."""

import json
import os
from typing import Any, Dict, Type

from materializers.prompt import Prompt
from materializers.prompt import Prompt as MaterializersPrompt
from materializers.prompt_visualizer import visualize_prompt_data
from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class PromptMaterializer(BaseMaterializer):
    """Materializer for Prompt objects."""

    ASSOCIATED_TYPES = (Prompt, MaterializersPrompt)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Prompt:
        """Load Prompt object from artifact store.

        Args:
            data_type: The type to load (Prompt)

        Returns:
            Loaded Prompt object
        """
        with fileio.open(os.path.join(self.uri, "prompt.json"), "r") as f:
            prompt_data = json.load(f)
        return Prompt.from_dict(prompt_data)

    def save(self, data: Any) -> None:
        """Save Prompt object to artifact store.

        Args:
            data: Prompt object to save

        Raises:
            ValueError: If data is not a Prompt object with required methods
        """
        # Ensure data has the required methods regardless of import path
        if not hasattr(data, "to_dict") or not hasattr(data, "name"):
            raise ValueError(
                f"Data must be a Prompt object with to_dict() and name attributes, got {type(data)}"
            )

        with fileio.open(os.path.join(self.uri, "prompt.json"), "w") as f:
            json.dump(data.to_dict(), f, indent=2)

        # Save the prompt content as a separate text file for easy viewing
        with fileio.open(
            os.path.join(self.uri, "prompt_content.txt"), "w"
        ) as f:
            f.write(f"=== {data.name} (v{data.version}) ===\n")
            f.write(f"Description: {data.description}\n")
            f.write(f"Variables: {data.get_variable_names()}\n")
            f.write(f"Created: {data.created_at}\n")
            f.write("=" * 50 + "\n")
            f.write(data.content)

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate and save visualizations for Prompt object.

        Args:
            data: Prompt object to visualize

        Returns:
            Dictionary mapping visualization file paths to their types
        """
        visualization_path = os.path.join(self.uri, "visualization.html")

        # Generate the HTML visualization
        html_content = visualize_prompt_data(data)

        # Save the visualization
        with fileio.open(visualization_path, "w") as f:
            f.write(html_content)

        return {visualization_path: VisualizationType.HTML}

    def extract_metadata(self, data: Any) -> Dict[str, Any]:
        """Extract metadata from Prompt object.

        Args:
            data: Prompt object to extract metadata from

        Returns:
            Metadata dictionary
        """
        return {
            "name": data.name,
            "version": data.version,
            "description": data.description,
            "variables": data.get_variable_names(),
            "content_length": len(data.content),
            "created_at": data.created_at.isoformat(),
            "author": data.author,
            "tags": data.tags,
        }
