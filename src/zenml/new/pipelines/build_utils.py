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
"""Pipeline build utilities."""

import hashlib
import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID, uuid4

import zenml
from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    BuildItem,
    CodeReferenceRequest,
    PipelineBuildBase,
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineDeploymentBase,
    PipelineDeploymentRequest,
)
from zenml.stack import Stack
from zenml.utils import (
    source_utils,
)
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.code_repositories import LocalRepositoryContext
    from zenml.config.build_configuration import BuildConfiguration

logger = get_logger(__name__)


def _create_deployment(
    deployment: "PipelineDeploymentBase",
    pipeline_id: Optional[UUID] = None,
    code_repository: Optional["BaseCodeRepository"] = None,
) -> UUID:
    """Creates a deployment in the ZenStore.

    Args:
        deployment: Base of the deployment to create.
        pipeline_id: Pipeline ID to use for the deployment.
        code_repository: Code repository to use for the deployment.

    Returns:
        The ID of the deployment.
    """
    source_root = source_utils.get_source_root()

    code_reference = None
    local_repo_context = (
        code_repository.get_local_context(source_root)
        if code_repository
        else None
    )
    if local_repo_context and not local_repo_context.is_dirty:
        subdirectory = (
            Path(source_root).resolve().relative_to(local_repo_context.root)
        )

        code_reference = CodeReferenceRequest(
            commit=local_repo_context.current_commit,
            subdirectory=subdirectory.as_posix(),
            code_repository=local_repo_context.code_repository_id,
        )

    deployment_request = PipelineDeploymentRequest(
        user=Client().active_user.id,
        workspace=Client().active_workspace.id,
        stack=Client().active_stack.id,
        pipeline=pipeline_id,
        code_reference=code_reference,
        **deployment.model_dump(),
    )
    return (
        Client().zen_store.create_deployment(deployment=deployment_request).id
    )


def build_required(deployment: "PipelineDeploymentBase") -> bool:
    """Checks whether a build is required for the deployment and active stack.

    Args:
        deployment: The deployment for which to check.

    Returns:
        If a build is required.
    """
    stack = Client().active_stack
    return bool(stack.get_docker_builds(deployment=deployment))


def reuse_or_create_pipeline_build(
    deployment: "PipelineDeploymentBase",
    allow_build_reuse: bool,
    pipeline_id: Optional[UUID] = None,
    build: Union["UUID", "PipelineBuildBase", None] = None,
    code_repository: Optional["BaseCodeRepository"] = None,
) -> Optional["PipelineBuildResponse"]:
    """Loads or creates a pipeline build.

    Args:
        deployment: The pipeline deployment for which to load or create the
            build.
        allow_build_reuse: If True, the build is allowed to reuse an
            existing build.
        pipeline_id: Optional ID of the pipeline to reference in the build.
        build: Optional existing build. If given, the build will be fetched
            (or registered) in the database. If not given, a new build will
            be created.
        code_repository: If provided, this code repository will be used to
            download inside the build images.

    Returns:
        The build response.
    """
    if not build:
        if (
            allow_build_reuse
            and not deployment.requires_included_files
            and build_required(deployment=deployment)
        ):
            existing_build = find_existing_build(
                deployment=deployment, code_repository=code_repository
            )

            if existing_build:
                logger.info(
                    "Reusing existing build `%s` for stack `%s`.",
                    existing_build.id,
                    Client().active_stack.name,
                )
                return existing_build
            else:
                logger.info(
                    "Unable to find a build to reuse. When using a code "
                    "repository, a previous build can be reused when the "
                    "following conditions are met:\n"
                    "  * The existing build was created for the same stack, "
                    "ZenML version and Python version\n"
                    "  * The stack contains a container registry\n"
                    "  * The Docker settings of the pipeline and all its steps "
                    "are the same as for the existing build\n"
                    "  * The build does not include code. This will only be "
                    "the case if the existing build was created with a clean "
                    "code repository."
                )

        return create_pipeline_build(
            deployment=deployment,
            pipeline_id=pipeline_id,
            code_repository=code_repository,
        )

    if isinstance(build, UUID):
        build_model = Client().zen_store.get_build(build_id=build)
    else:
        build_request = PipelineBuildRequest(
            user=Client().active_user.id,
            workspace=Client().active_workspace.id,
            stack=Client().active_stack_model.id,
            pipeline=pipeline_id,
            **build.model_dump(),
        )
        build_model = Client().zen_store.create_build(build=build_request)

    verify_custom_build(
        build=build_model,
        deployment=deployment,
        code_repository=code_repository,
    )

    return build_model


def find_existing_build(
    deployment: "PipelineDeploymentBase",
    code_repository: "BaseCodeRepository",
) -> Optional["PipelineBuildResponse"]:
    """Find an existing build for a deployment.

    Args:
        deployment: The deployment for which to find an existing build.
        code_repository: The code repository that will be used to download
            files in the images.

    Returns:
        The existing build to reuse if found.
    """
    client = Client()
    stack = client.active_stack

    python_version_prefix = ".".join(platform.python_version_tuple()[:2])
    required_builds = stack.get_docker_builds(deployment=deployment)

    if not required_builds:
        return None

    build_checksum = compute_build_checksum(
        required_builds, stack=stack, code_repository=code_repository
    )

    matches = client.list_builds(
        sort_by="desc:created",
        size=1,
        stack_id=stack.id,
        # The build is local and it's not clear whether the images
        # exist on the current machine or if they've been overwritten.
        # TODO: Should we support this by storing the unique Docker ID for
        #   the image and checking if an image with that ID exists locally?
        is_local=False,
        # The build contains some code which might be different from the
        # local code the user is expecting to run
        contains_code=False,
        zenml_version=zenml.__version__,
        # Match all patch versions of the same Python major + minor
        python_version=f"startswith:{python_version_prefix}",
        checksum=build_checksum,
    )

    if not matches.items:
        return None

    return matches[0]


def create_pipeline_build(
    deployment: "PipelineDeploymentBase",
    pipeline_id: Optional[UUID] = None,
    code_repository: Optional["BaseCodeRepository"] = None,
) -> Optional["PipelineBuildResponse"]:
    """Builds images and registers the output in the server.

    Args:
        deployment: The pipeline deployment.
        pipeline_id: The ID of the pipeline.
        code_repository: If provided, this code repository will be used to
            download inside the build images.

    Returns:
        The build output.

    Raises:
        RuntimeError: If multiple builds with the same key but different
            settings were specified.
    """
    client = Client()
    stack = client.active_stack
    required_builds = stack.get_docker_builds(deployment=deployment)

    if not required_builds:
        logger.debug("No docker builds required.")
        return None

    logger.info(
        "Building Docker image(s) for pipeline `%s`.",
        deployment.pipeline_configuration.name,
    )

    docker_image_builder = PipelineDockerImageBuilder()
    images: Dict[str, BuildItem] = {}
    checksums: Dict[str, str] = {}

    for build_config in required_builds:
        combined_key = PipelineBuildBase.get_image_key(
            component_key=build_config.key, step=build_config.step_name
        )
        checksum = build_config.compute_settings_checksum(
            stack=stack, code_repository=code_repository
        )

        if combined_key in images:
            previous_checksum = images[combined_key].settings_checksum

            if previous_checksum != checksum:
                raise RuntimeError(
                    f"Trying to build image for key `{combined_key}` but "
                    "an image for this key was already built with a "
                    "different configuration. This happens if multiple "
                    "stack components specified Docker builds for the same "
                    "key in the `StackComponent.get_docker_builds(...)` "
                    "method. If you're using custom components, make sure "
                    "to provide unique keys when returning your build "
                    "configurations to avoid this error."
                )
            else:
                continue

        if checksum in checksums:
            item_key = checksums[checksum]
            image_name_or_digest = images[item_key].image
            contains_code = images[item_key].contains_code
            dockerfile = images[item_key].dockerfile
            requirements = images[item_key].requirements
        else:
            tag = deployment.pipeline_configuration.name
            if build_config.step_name:
                tag += f"-{build_config.step_name}"
            tag += f"-{build_config.key}"

            include_files = build_config.should_include_files(
                code_repository=code_repository,
            )
            download_files = build_config.should_download_files(
                code_repository=code_repository,
            )

            (
                image_name_or_digest,
                dockerfile,
                requirements,
            ) = docker_image_builder.build_docker_image(
                docker_settings=build_config.settings,
                tag=tag,
                stack=stack,
                include_files=include_files,
                download_files=download_files,
                entrypoint=build_config.entrypoint,
                extra_files=build_config.extra_files,
                code_repository=code_repository,
            )
            contains_code = include_files

        images[combined_key] = BuildItem(
            image=image_name_or_digest,
            dockerfile=dockerfile,
            requirements=requirements,
            settings_checksum=checksum,
            contains_code=contains_code,
            requires_code_download=download_files,
        )
        checksums[checksum] = combined_key

    logger.info("Finished building Docker image(s).")

    is_local = stack.container_registry is None
    contains_code = any(item.contains_code for item in images.values())
    build_checksum = compute_build_checksum(
        required_builds, stack=stack, code_repository=code_repository
    )
    template_deployment_id = _create_deployment(
        deployment=deployment,
        pipeline_id=pipeline_id,
        code_repository=code_repository,
    )

    build_request = PipelineBuildRequest(
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        stack=client.active_stack_model.id,
        pipeline=pipeline_id,
        is_local=is_local,
        contains_code=contains_code,
        images=images,
        zenml_version=zenml.__version__,
        python_version=platform.python_version(),
        checksum=build_checksum,
        template_deployment_id=template_deployment_id,
    )
    return client.zen_store.create_build(build_request)


def compute_build_checksum(
    items: List["BuildConfiguration"],
    stack: "Stack",
    code_repository: Optional["BaseCodeRepository"] = None,
) -> str:
    """Compute an overall checksum for a pipeline build.

    Args:
        items: Items of the build.
        stack: The stack associated with the build. Will be used to gather
            its requirements.
        code_repository: The code repository that will be used to download
            files inside the build. Will be used for its dependency
            specification.

    Returns:
        The build checksum.
    """
    hash_ = hashlib.md5()  # nosec

    for item in items:
        key = PipelineBuildBase.get_image_key(
            component_key=item.key, step=item.step_name
        )

        settings_checksum = item.compute_settings_checksum(
            stack=stack,
            code_repository=code_repository,
        )

        hash_.update(key.encode())
        hash_.update(settings_checksum.encode())

    return hash_.hexdigest()


def upload_code_repository() -> Optional[str]:
    """Downloads all files from the git repo, zips them, and uploads to the artifact store.

    Returns:
        A path to a zipfile with all the code repo.
    """
    artifact_store = Client().active_stack.artifact_store
    if artifact_store.config.is_local:
        return None

    source_root = source_utils.get_source_root()

    try:
        # Create a temporary directory to store the dirty files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a zip file
            zip_filename = f"dirty_files_{uuid4()}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            shutil.make_archive(zip_path, "zip", source_root)

            # Upload the zip file to the artifact store
            artifact_uri = f"{artifact_store.path}/{zip_filename}"

            # Copy to artifact store
            fileio.copy(zip_path, artifact_uri)

            logger.info(f"Uploaded dirty files to {artifact_uri}")
            return artifact_uri

    except Exception as e:
        raise RuntimeError(f"Error while processing dirty files: {str(e)}")


def verify_local_repository_context(
    deployment: "PipelineDeploymentBase",
    local_repo_context: Optional["LocalRepositoryContext"],
) -> Optional[BaseCodeRepository]:
    """Verifies the local repository.

    If the local repository exists and has no local changes, code download
    inside the images is possible.

    Args:
        deployment: The pipeline deployment.
        local_repo_context: The local repository active at the source root.

    Returns:
        The code repository from which to download files for the runs of the
        deployment, or None if code download is not possible.
    """
    if build_required(deployment=deployment):
        if deployment.requires_code_download:
            if not local_repo_context:
                logger.warning(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be included in the "
                    "Docker image (`source_files='download'`), but there is no "
                    "code repository active at your current source root "
                    f"`{source_utils.get_source_root()}`."
                )
            elif local_repo_context.is_dirty:
                logger.warning(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be included in the "
                    "Docker image (`source_files='download'`), but the code "
                    "repository active at your current source root "
                    f"`{source_utils.get_source_root()}` has uncommitted "
                    "changes."
                )
            elif local_repo_context.has_local_changes:
                logger.warning(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be included in the "
                    "Docker image (`source_files='download'`), but the code "
                    "repository active at your current source root "
                    f"`{source_utils.get_source_root()}` has unpushed "
                    "changes."
                )

        if local_repo_context:
            if local_repo_context.is_dirty:
                logger.warning(
                    "Unable to use code repository to download code for this run "
                    "as there are uncommitted changes."
                )
            elif local_repo_context.has_local_changes:
                logger.warning(
                    "Unable to use code repository to download code for this run "
                    "as there are unpushed changes."
                )

    code_repository = None
    if local_repo_context and not local_repo_context.has_local_changes:
        model = Client().get_code_repository(
            local_repo_context.code_repository_id
        )
        code_repository = BaseCodeRepository.from_model(model)

    return code_repository


def verify_custom_build(
    build: "PipelineBuildResponse",
    deployment: "PipelineDeploymentBase",
    code_repository: Optional["BaseCodeRepository"] = None,
) -> None:
    """Verify a custom build for a pipeline deployment.

    Args:
        build: The build to verify.
        deployment: The deployment for which to verify the build.
        code_repository: Code repository that will be used to download files
            for the deployment.

    Raises:
        RuntimeError: If the build can't be used for the deployment.
    """
    stack = Client().active_stack
    required_builds = stack.get_docker_builds(deployment=deployment)

    if build.stack and build.stack.id != stack.id:
        logger.warning(
            "The stack `%s` used for the build `%s` is not the same as the "
            "stack `%s` that the pipeline will run on. This could lead "
            "to issues if the stacks have different build requirements.",
            build.stack.name,
            build.id,
            stack.name,
        )

    if build.contains_code:
        logger.warning(
            "The build you specified for this run contains code and will run "
            "with the step code that was included in the Docker images which "
            "might differ from the local code in your client environment."
        )

    if build.requires_code_download and not code_repository:
        raise RuntimeError(
            "The build you specified does not include code but code download "
            "not possible. This might be because you don't have a code "
            "repository registered or the code repository contains local "
            "changes."
        )

    if build.checksum:
        build_checksum = compute_build_checksum(
            required_builds, stack=stack, code_repository=code_repository
        )
        if build_checksum != build.checksum:
            logger.warning(
                "The Docker settings used for the build `%s` are "
                "not the same as currently specified for your pipeline. "
                "This means that the build you specified to run this "
                "pipeline might be outdated and most likely contains "
                "outdated requirements.",
                build.id,
            )
    else:
        # No checksum given for the entire build, we manually check that
        # all the images exist and the setting match
        for build_config in required_builds:
            try:
                image = build.get_image(
                    component_key=build_config.key,
                    step=build_config.step_name,
                )
            except KeyError:
                raise RuntimeError(
                    "The build you specified is missing an image for key: "
                    f"{build_config.key}."
                )

            if build_config.compute_settings_checksum(
                stack=stack, code_repository=code_repository
            ) != build.get_settings_checksum(
                component_key=build_config.key, step=build_config.step_name
            ):
                logger.warning(
                    "The Docker settings used to build the image `%s` are "
                    "not the same as currently specified for your pipeline. "
                    "This means that the build you specified to run this "
                    "pipeline might be outdated and most likely contains "
                    "outdated code or requirements.",
                    image,
                )

    if build.is_local:
        logger.warning(
            "You manually specified a local build to run your pipeline. "
            "This might lead to errors if the images don't exist on "
            "your local machine or the image tags have been "
            "overwritten since the original build happened."
        )
