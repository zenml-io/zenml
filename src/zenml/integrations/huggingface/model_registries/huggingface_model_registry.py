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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, cast
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

    MODELCARD_TEMPLATE_PATH: ClassVar[str] = f"{uuid4()}.md"
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
        old_card: ModelCard = None,
        revision: str = None,
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
            if old_card is None or old_card.content != card.content:
                card.push_to_hub(
                    token=self.config.token,
                    repo_id=self._repo_id(name),
                    repo_type=self.REPO_TYPE,
                    revision=revision,
                )

    def _get_model_card_content(
        self,
        name: str,
        revision: Optional[str] = None,
        drop_metadata: bool = False,
    ) -> Tuple[str, Dict[str, Any], ModelCard]:
        tmpdir = str(uuid4())
        os.mkdir(tmpdir)
        self.api.hf_hub_download(
            repo_id=self._repo_id(name),
            filename="README.md",
            local_dir=tmpdir,
            revision=revision,
        )

        card = ModelCard.load(
            repo_id_or_path=os.path.join(tmpdir, "README.md"),
        )
        metadata = {}
        description = None
        for k, v in card.data.to_dict().items():
            if k == "description":
                description = description or v
            elif not drop_metadata:
                metadata[k] = v

        os.remove(os.path.join(tmpdir, "README.md"))
        os.rmdir(tmpdir)

        return description, metadata, card

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
        if self.api.repo_exists(self._repo_id(name)):
            raise RuntimeError(f"Model `{name}` already exists.")

        self.api.create_repo(
            repo_id=self._repo_id(name),
            repo_type=self.REPO_TYPE,
            exist_ok=False,
        )

        self._push_model_card(
            name=name,
            description=description,
            metadata=metadata if metadata else {},
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
        self._model_exists(name)
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
            remove_metadata: The metadata to remove from the registered model. (["*"] removes all)
            revision: The revision to update model card in.
        """
        self._model_exists(name)

        found_description, found_metadata, card = self._get_model_card_content(
            name, revision, remove_metadata == ["*"]
        )

        remove_metadata = remove_metadata or []
        metadata.update(
            {
                k: v
                for k, v in found_metadata.items()
                if k not in remove_metadata
            }
        )

        self._push_model_card(
            name=name,
            description=description or found_description,
            metadata=metadata if metadata else {},
            revision=revision,
            old_card=card,
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

        pr_title = f"New model version from ZenML"
        pr = self.api.create_pull_request(
            repo_id=self._repo_id(name),
            title=pr_title,
            repo_type=self.REPO_TYPE,
        )
        pr_ref = f"refs/pr/{pr.num}"
        if version is not None:
            logger.warning(
                "There is no way to control versioning on Huggingface. "
                f"You can refer to new version as {pr_ref} in future."
            )

        upload_folder_path = os.path.abspath(model_source_uri)
        if os.path.isfile(upload_folder_path):
            upload_folder_path = os.path.dirname(upload_folder_path)
        self.api.upload_folder(
            folder_path=upload_folder_path,
            repo_id=self._repo_id(name),
            repo_type="model",
            revision=pr_ref,
        )
        self.update_model(
            name=name,
            description=description,
            metadata=metadata.dict() if metadata is not None else {},
            revision=pr_ref,
            remove_metadata=["*"],
        )

        self.api.change_discussion_status(
            repo_id=self._repo_id(name),
            repo_type=self.REPO_TYPE,
            discussion_num=pr.num,
            new_status="open",
        )

        return ModelVersion(
            version=pr_ref,
            model_source_uri=pr.url,
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

        for discussion in self.api.get_repo_discussions(
            repo_id=self._repo_id(name), repo_type=self.REPO_TYPE
        ):
            if discussion.is_pull_request and discussion.url.endswith(
                f"discussions/{version.split('/')[-1]}"
            ):
                self.api.change_discussion_status(
                    repo_id=self._repo_id(name),
                    repo_type=self.REPO_TYPE,
                    discussion_num=discussion.num,
                    new_status="closed",
                )
                break

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
        registered_model = self.update_model(
            name=name,
            description=description,
            metadata=metadata.dict() if metadata else {},
            remove_metadata=remove_metadata,
            revision=version,
        )
        pr_num = version.split("/")[-1]
        if stage:
            if (
                stage != ModelVersionStage.PRODUCTION
                and stage != ModelVersionStage.PRODUCTION.value
            ):
                raise RuntimeError(
                    "Only `ModelVersionStage.PRODUCTION` stage is supported with Huggingface at the moment."
                )
            for discussion in self.api.get_repo_discussions(
                repo_id=self._repo_id(name), repo_type=self.REPO_TYPE
            ):
                if discussion.is_pull_request and discussion.url.endswith(
                    f"discussions/{pr_num}"
                ):
                    if discussion.status != "open":
                        raise RuntimeError(
                            f"Cannot merge non `open` Pull Requests. Check the status {discussion.url}"
                        )
                    self.api.merge_pull_request(
                        repo_id=self._repo_id(name),
                        discussion_num=discussion.num,
                        comment="Promoted from ZenML",
                        repo_type=self.REPO_TYPE,
                    )
                    break

        return ModelVersion(
            version=version,
            model_source_uri=f"https://huggingface.co/avishniakov/{name}/discussions/{pr_num}",
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
        models = self.list_models(name=name, metadata={})

        fetched_versions = []
        for model in models:
            for discussion in self.api.get_repo_discussions(
                repo_id=self._repo_id(model.name), repo_type=self.REPO_TYPE
            ):
                if (
                    discussion.is_pull_request
                    and discussion.title == "New model version from ZenML"
                ):
                    if discussion.status == "open":
                        pr_ref = f"refs/pr/{discussion.num}"
                        (
                            description,
                            found_metadata,
                            _,
                        ) = self._get_model_card_content(model.name, pr_ref)
                        metadata_filter = True
                        if metadata is not None:
                            for k, v in metadata.dict().items():
                                metadata_filter &= (
                                    k in found_metadata
                                    and found_metadata[k] == v
                                )
                                if not metadata_filter:
                                    break
                        if metadata_filter:
                            fetched_versions.append(
                                ModelVersion(
                                    version=pr_ref,
                                    model_source_uri=discussion.url,
                                    model_format="hugginface",
                                    registered_model=model,
                                    description=description,
                                    metadata=found_metadata,
                                )
                            )
        return fetched_versions

    def get_model_version(self, name: str, version: str) -> ModelVersion:
        """Gets a model version for a registered model.

        Args:
            name: The name of the registered model.
            version: The version of the model version to get.

        Returns:
            The model version.
        """
        pr_num = version.split("/")[-1]
        description, metadata, _ = self._get_model_card_content(
            name=name, revision=version
        )
        return ModelVersion(
            version=version,
            model_source_uri=f"https://huggingface.co/{self._repo_id(name)}/discussions/{pr_num}",
            model_format="hugginface",
            registered_model=self.get_model(name),
            description=description,
            metadata=metadata,
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

        files = self.api.list_repo_files(
            repo_id=self._repo_id(name),
            revision=version,
            repo_type=self.REPO_TYPE,
        )

        download_folder_path = os.path.abspath(path)
        if not os.path.exists(download_folder_path):
            os.makedirs(download_folder_path)

        for file in files:
            self.api.hf_hub_download(
                repo_id=self._repo_id(name),
                filename=file,
                local_dir=download_folder_path,
                revision=version,
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
