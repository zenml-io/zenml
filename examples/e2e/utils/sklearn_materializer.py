import json
import os
from typing import Any, Dict, Type

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class ModelInfoMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (dict,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[dict]) -> Dict[str, Any]:
        """Read from artifact store.

        Args:
            data_type: What type the artifact data should be loaded as.

        Raises:
            ValueError: on deserialization issue

        Returns:
            Read artifact.
        """
        import sklearn.ensemble
        import sklearn.linear_model
        import sklearn.tree

        modules = [sklearn.ensemble, sklearn.linear_model, sklearn.tree]

        with fileio.open(os.path.join(self.uri, "data.json"), "r") as f:
            data = json.loads(f.read())
        class_name = data["class"]
        cls = None
        for module in modules:
            try:
                cls = getattr(module, class_name)
                break
            except:
                pass
        if cls is None:
            raise ValueError(
                f"Cannot deserialize `{class_name}` using {self.__class__.__name__}. "
                f"Only classes from modules {[m.__name__ for m in modules]} "
                "are supported"
            )
        data["class"] = cls

        return data

    def save(self, data: dict) -> None:
        """Write to artifact store.

        Args:
            data: The data of the artifact to save.
        """
        with fileio.open(os.path.join(self.uri, "data.json"), "w") as f:
            data["class"] = data["class"].__name__
            f.write(json.dumps(data))
