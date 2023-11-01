#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the MLflow model registry for ZenML."""


import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, cast
from uuid import uuid4

from huggingface_hub import HfApi, ModelCard, ModelCardData

from zenml.integrations.huggingface.flavors.huggingface_model_registry_flavor import (
    HuggingfaceModelRegistryConfig,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistryModelMetadata,
    ModelVersion,
    ModelVersionStage,
    RegisteredModel,
)

logger = get_logger(__name__)


class HuggingfaceRegisteredModel(RegisteredModel):
    """Huggingface registered model class."""

    repo_id: str


class HuggingfaceModelRegistry(BaseModelRegistry):
    """Register models using Huggingface."""

    MODELCARD_TEMPLATE_PATH: ClassVar[str] = "zenml_template.md"
    REPO_TYPE: ClassVar[str] = "model"

    @property
    def config(self) -> HuggingfaceModelRegistryConfig:
        """Returns the `HuggingfaceModelRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(HuggingfaceModelRegistryConfig, self._config)

    @property
    def api(self) -> HfApi:
        return HfApi(token=self.config.token)

    def _model_exists(self, name: str):
        if not self.api.repo_exists(
            repo_id=self._repo_id(name), repo_type=self.REPO_TYPE
        ):
            raise KeyError(
                f"Model with name `{self._repo_id(name)}` doesn't exist."
            )

    @contextmanager
    def model_card_template(self):
        template_text = """
---
{{ card_data }}
---
# {{ model_name }}

## Description
{{ model_description }}

## Metadata
{% for key,value in metadata.items() %}
{{ key }}:  {{ value }}
{% endfor %}

_This model was created from **ZenML**_
""".strip()
        Path(self.MODELCARD_TEMPLATE_PATH).write_text(template_text)
        yield
        os.remove(self.MODELCARD_TEMPLATE_PATH)

    def _repo_id(self, name: str) -> str:
        return f"{self.config.user}/{name}"

    def _push_model_card(
        self,
        name: str,
        description: str,
        metadata: Dict[str, str],
    ):
        with self.model_card_template():
            card = ModelCard.from_template(
                card_data=ModelCardData(
                    **metadata,
                    description=description,
                ),
                model_name=name,
                model_description=description,
                template_path=self.MODELCARD_TEMPLATE_PATH,
                metadata=metadata,
            )
            card.push_to_hub(
                token=self.config.token,
                repo_id=self._repo_id(name),
                repo_type=self.REPO_TYPE,
            )

    # ---------
    # Model Registration Methods
    # ---------

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Registers a model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            metadata: The metadata associated with the registered model.

        Returns:
            The registered model.
        """
        self.api.create_repo(
            repo_id=self._repo_id(name),
            repo_type=self.REPO_TYPE,
            exist_ok=False,
        )

        self._push_model_card(
            name=name,
            description=description,
            metadata=metadata,
        )

        return RegisteredModel(
            name=name,
            description=description,
            metadata=metadata,
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Deletes a registered model from the model registry.

        Args:
            name: The name of the registered model.
        """
        self._model_exists()
        self.api.delete_repo(repo_id=name)

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
        revision: Optional[str] = None,
    ) -> RegisteredModel:
        """Updates a registered model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            metadata: The metadata associated with the registered model.
            remove_metadata: The metadata to remove from the registered model.
            revision: The revision to update model card in.
        """
        self._model_exists()

        card = ModelCard.load(
            token=self.config.token,
            repo_id_or_path=self._repo_id(name),
            repo_type=self.REPO_TYPE,
        )

        remove_metadata = remove_metadata or []
        for k, v in card.data.to_dict().items():
            if k not in remove_metadata:
                if k == "description":
                    description = description or v
                else:
                    metadata[k] = v

        self._push_model_card(
            name=name,
            description=description,
            metadata=metadata,
            revision=revision,
        )

        return RegisteredModel(
            name=name,
            description=description,
            metadata=metadata,
        )

    def get_model(self, name: str) -> RegisteredModel:
        """Gets a registered model from the model registry.

        Args:
            name: The name of the registered model.

        Returns:
            The registered model.

        Raises:
            zenml.exceptions.EntityExistsError: If the model does not exist.
            RuntimeError: If retrieval fails.
        """
        self._model_exists(name)

        card = ModelCard.load(
            token=self.config.token,
            repo_id_or_path=self._repo_id(name),
            repo_type=self.REPO_TYPE,
        )

        metadata = card.data.to_dict()
        description = metadata.get("description", None)
        if "description" in metadata:
            metadata.pop("description")

        return RegisteredModel(
            name=name,
            description=description,
            metadata=metadata,
        )

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """Lists all registered models in the model registry.

        Args:
            name: The name of the registered model.
            metadata: The metadata associated with the registered model.

        Returns:
            A list of registered models.
        """
        fetched_models = []
        for model in self.api.list_models(author=self.config.user):
            found_name = model.modelId.split("/")[1]

            card = ModelCard.load(
                token=self.config.token,
                repo_id_or_path=model.modelId,
                repo_type=self.REPO_TYPE,
            )

            found_metadata = card.data.to_dict()
            description = found_metadata.get("description", None)
            if "description" in found_metadata:
                found_metadata.pop("description")

            name_filter = name is None or found_name == name

            metadata_filter = True
            if metadata is not None and name_filter:
                for k, v in metadata.items():
                    metadata_filter &= (
                        k in found_metadata and found_metadata[k] == v
                    )
                    if not metadata_filter:
                        break

            if name_filter and metadata_filter:
                fetched_models.append(
                    RegisteredModel(
                        name=found_name,
                        description=description,
                        metadata=found_metadata,
                    )
                )
        return fetched_models

    # ---------
    # Model Version Methods
    # ---------

    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> ModelVersion:
        """Registers a model version in the model registry.

        Args:
            name: The name of the registered model.
            model_source_uri: The source URI of the model.
            version: The version of the model version.
            description: The description of the model version.
            metadata: The metadata associated with the model
                version.
            **kwargs: Ignored.

        Returns:
            The registered model version.

        Raises:
            RuntimeError: If registration fails.
        """

        self._model_exists(name)

        for ref in self.api.list_repo_refs(
            repo_id=self._repo_id(name),
            repo_type=self.REPO_TYPE,
        ).tags:
            if ref.name == version:
                raise RuntimeError(
                    f"Model version `{version}` already registered."
                )

        if version is None:
            version = str(uuid4())

        upload_folder_path = os.path.abspath(model_source_uri)
        if os.path.isfile(upload_folder_path):
            upload_folder_path = os.path.dirname(upload_folder_path)
        self.api.upload_folder(
            folder_path=upload_folder_path,
            repo_id=self._repo_id(name),
            repo_type="model",
        )
        self._push_model_card(
            name=name,
            description=description,
            metadata=metadata.dict() if metadata is not None else {},
        )
        self.api.create_tag(
            repo_id=self._repo_id(name),
            tag=version,
            tag_message=description,
            repo_type=self.REPO_TYPE,
        )
        return ModelVersion(
            version=version,
            model_source_uri=f"https://huggingface.co/{self._repo_id(name)}/tree/{version}",
            model_format="hugginface",
            registered_model=self.get_model(name),
            description=description,
            metadata=metadata,
        )

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Deletes a model version from the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to delete.
        """
        self._model_exists(name)

        self.api.delete_tag(
            repo_id=self._repo_id(name),
            tag=version,
            repo_type=self.REPO_TYPE,
        )

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> ModelVersion:
        """Updates a model version in the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to update.
            description: The description of the model version.
            metadata: Metadata associated with this model version.
            remove_metadata: The metadata to remove from the model version.
            stage: Not supported in Huggingface.

        Returns:
            The updated model version.

        Raises:
            KeyError: If the model version does not exist.
            RuntimeError: If update fails.
        """
        self.api.delete_tag(
            repo_id=self._repo_id(name),
            tag=version,
            repo_type=self.REPO_TYPE,
        )
        registered_model = self.update_model(
            name=name,
            description=description,
            metadata=metadata.dict(),
            remove_metadata=remove_metadata,
        )
        self.api.create_tag(
            repo_id=self._repo_id(name),
            tag=version,
            tag_message=description,
            repo_type=self.REPO_TYPE,
        )

        return ModelVersion(
            version=version,
            model_source_uri=f"https://huggingface.co/{self._repo_id(name)}/tree/{version}",
            model_format="hugginface",
            registered_model=registered_model,
            description=description,
            metadata=metadata,
        )

    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        stage: Optional[ModelVersionStage] = None,
        count: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        order_by_date: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[List[ModelVersion]]:
        """Lists all model versions for a registered model.

        Args:
            name: The name of the registered model.
            model_source_uri: The model source URI of the registered model.
            metadata: Metadata associated with this model version.
            stage: The stage of the model version.
            count: The number of model versions to return.
            created_after: The timestamp after which to list model versions.
            created_before: The timestamp before which to list model versions.
            order_by_date: Whether to sort by creation time, this can
                be "asc" or "desc".
            kwargs: Additional keyword arguments.

        Returns:
            A list of model versions.
        """
        models = self.list_models(
            name=name, metadata=metadata.dict() if metadata is not None else {}
        )

        fetched_versions = []
        for model in models:
            for ref in self.api.list_repo_refs(
                repo_id=self._repo_id(model.name),
                repo_type=self.REPO_TYPE,
            ).tags:
                if name is not None and ref.name != name:
                    continue

                fetched_versions.append(
                    ModelVersion(
                        version=ref.name,
                        model_source_uri=f"https://huggingface.co/{self._repo_id(model.name)}/tree/{ref.name}",
                        model_format="hugginface",
                        registered_model=model,
                        description=None,
                        metadata=metadata,
                    )
                )

    def get_model_version(self, name: str, version: str) -> ModelVersion:
        """Gets a model version for a registered model.

        Args:
            name: The name of the registered model.
            version: The version of the model version to get.

        Returns:
            The model version.
        """

        return ModelVersion(
            version=version,
            model_source_uri=f"https://huggingface.co/{self._repo_id(name)}/tree/{version}",
            model_format="hugginface",
            registered_model=self.get_model(name),
            description=None,
            metadata=None,
        )

    def load_model_version(
        self,
        name: str,
        version: str,
        path: str,
        **kwargs: Any,
    ) -> None:
        """Loads a model version from the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to load.
            path: The path to load model into.
            **kwargs: Additional keyword arguments.

        Returns:
            None.
        """
        from zenml.client import Client

        files = self.api.list_repo_files(
            repo_id=self._repo_id(name),
            revision=version,
            repo_type=self.REPO_TYPE,
        )

        zenml_repo_root = Client().root
        if not zenml_repo_root:
            raise RuntimeError(
                "You're running the `load_model_version` outside of a ZenML repo."
                "Since the deployment step to huggingface is all about pushing the repo to huggingface, "
                f"this step will not work outside of a ZenML repo where the `{path}` folder is present."
            )
        download_folder_path = os.path.abspath(path)
        if not os.path.exists(download_folder_path):
            os.makedirs(download_folder_path)

        for file in files:
            self.api.hf_hub_download(
                repo_id=self._repo_id(name),
                filename=file,
                local_dir=download_folder_path,
            )

    def get_model_uri_artifact_store(
        self,
        model_version: ModelVersion,
    ) -> str:
        """Gets the URI artifact store for a model version.

        This method retrieves the URI of the artifact store for a specific model
        version. Its purpose is to ensure that the URI is in the correct format
        for the specific artifact store being used. This is essential for the
        model serving component, which relies on the URI to serve the model
        version. In some cases, the URI may be stored in a different format by
        certain model registry integrations. This method allows us to obtain the
        URI in the correct format, regardless of the integration being used.

        Note: In some cases the URI artifact store may not be available to the
        user, the method should save the target model in one of the other
        artifact stores supported by ZenML and return the URI of that artifact
        store.

        Args:
            model_version: The model version for which to get the URI artifact
                store.

        Returns:
            The URI artifact store for the model version.
        """
        raise NotImplementedError
