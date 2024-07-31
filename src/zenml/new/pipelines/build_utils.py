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
import tempfile
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

import zenml
from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository
from zenml.config.docker_settings import SourceFileMode
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    BuildItem,
    CodeReferenceRequest,
    PipelineBuildBase,
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineDeploymentBase,
    StackResponse,
)
from zenml.new.pipelines.code_archive import CodeArchive
from zenml.stack import Stack
from zenml.utils import source_utils, string_utils
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.code_repositories import LocalRepositoryContext
    from zenml.config.build_configuration import BuildConfiguration

logger = get_logger(__name__)


def build_required(deployment: "PipelineDeploymentBase") -> bool:
    """Checks whether a build is required for the deployment and active stack.

    Args:
        deployment: The deployment for which to check.

    Returns:
        If a build is required.
    """
    stack = Client().active_stack
    return bool(stack.get_docker_builds(deployment=deployment))


def requires_included_code(
    deployment: "PipelineDeploymentBase",
    code_repository: Optional["BaseCodeRepository"] = None,
) -> bool:
    """Checks whether the deployment requires included code.

    Args:
        deployment: The deployment.
        code_repository: If provided, this code repository can be used to
            download the code inside the container images.

    Returns:
        If the deployment requires code included in the container images.
    """
    for step in deployment.step_configurations.values():
        if step.config.docker_settings.source_files == [
            SourceFileMode.INCLUDE
        ]:
            return True

        if (
            step.config.docker_settings.source_files
            == [
                SourceFileMode.DOWNLOAD_FROM_CODE_REPOSITORY,
                SourceFileMode.INCLUDE,
            ]
            and not code_repository
        ):
            return True

    return False


def requires_download_from_code_repository(
    deployment: "PipelineDeploymentBase",
) -> bool:
    """Checks whether the deployment needs to download code from a repository.

    Args:
        deployment: The deployment.

    Returns:
        If the deployment needs to download code from a code repository.
    """
    return any(
        step.config.docker_settings.source_files
        == [
            SourceFileMode.DOWNLOAD_FROM_CODE_REPOSITORY,
        ]
        for step in deployment.step_configurations.values()
    )


def code_download_possible(
    deployment: "PipelineDeploymentBase",
    code_repository: Optional["BaseCodeRepository"] = None,
) -> bool:
    """Checks whether code download is possible for the deployment.

    Args:
        deployment: The deployment.
        code_repository: If provided, this code repository can be used to
            download the code inside the container images.

    Returns:
        Whether code download is possible for the deployment.
    """
    for step in deployment.step_configurations.values():
        if (
            SourceFileMode.DOWNLOAD_FROM_ARTIFACT_STORE
            in step.config.docker_settings.source_files
        ):
            continue

        if (
            SourceFileMode.DOWNLOAD_FROM_CODE_REPOSITORY
            in step.config.docker_settings.source_files
            and code_repository
        ):
            continue

        return False

    return True


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
        code_repository: If provided, this code repository can be used to
            download code inside the container images.

    Returns:
        The build response.
    """
    if not build:
        if (
            allow_build_reuse
            and not deployment.should_prevent_build_reuse
            and not requires_included_code(
                deployment=deployment, code_repository=code_repository
            )
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
                    "Unable to find a build to reuse. A previous build can be "
                    "reused when the following conditions are met:\n"
                    "  * The existing build was created for the same stack, "
                    "ZenML version and Python version\n"
                    "  * The stack contains a container registry\n"
                    "  * The Docker settings of the pipeline and all its steps "
                    "are the same as for the existing build."
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
    code_repository: Optional["BaseCodeRepository"] = None,
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
    stack_model = Client().active_stack_model
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
            pass_code_repo = (
                build_config.should_download_files_from_code_repository(
                    code_repository=code_repository
                )
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
                code_repository=code_repository if pass_code_repo else None,
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
    stack_checksum = compute_stack_checksum(stack=stack_model)
    build_request = PipelineBuildRequest(
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        stack=stack_model.id,
        pipeline=pipeline_id,
        is_local=is_local,
        contains_code=contains_code,
        images=images,
        zenml_version=zenml.__version__,
        python_version=platform.python_version(),
        checksum=build_checksum,
        stack_checksum=stack_checksum,
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

    Raises:
        RuntimeError: If the deployment requires code download but code download
            is not possible.

    Returns:
        The code repository from which to download files for the runs of the
        deployment, or None if code download is not possible.
    """
    if build_required(deployment=deployment):
        if requires_download_from_code_repository(deployment=deployment):
            if not local_repo_context:
                raise RuntimeError(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be downloaded from a "
                    "code repository "
                    "(`source_files=['download_from_code_repository']`), but "
                    "there is no code repository active at your current source "
                    f"root `{source_utils.get_source_root()}`."
                )
            elif local_repo_context.is_dirty:
                raise RuntimeError(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be downloaded from a "
                    "code repository "
                    "(`source_files=['download_from_code_repository']`), but "
                    "the code repository active at your current source root "
                    f"`{source_utils.get_source_root()}` has uncommitted "
                    "changes."
                )
            elif local_repo_context.has_local_changes:
                raise RuntimeError(
                    "The `DockerSettings` of the pipeline or one of its "
                    "steps specify that code should be downloaded from a "
                    "code repository "
                    "(`source_files=['download_from_code_repository']`), but "
                    "the code repository active at your current source root "
                    f"`{source_utils.get_source_root()}` has unpushed "
                    "changes."
                )

        if local_repo_context:
            if local_repo_context.is_dirty:
                logger.warning(
                    "Unable to use code repository to download code for this "
                    "run as there are uncommitted changes."
                )
            elif local_repo_context.has_local_changes:
                logger.warning(
                    "Unable to use code repository to download code for this "
                    "run as there are unpushed changes."
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

    if build.requires_code_download:
        if requires_included_code(
            deployment=deployment, code_repository=code_repository
        ):
            raise RuntimeError(
                "The `DockerSettings` of the pipeline or one of its "
                "steps specify that code should be included in the Docker "
                "image (`source_files=['include']`), but the build you "
                "specified requires code download. Either update your "
                "`DockerSettings` or specify a different build and try "
                "again."
            )

        if (
            requires_download_from_code_repository(deployment=deployment)
            and not code_repository
        ):
            raise RuntimeError(
                "The `DockerSettings` of the pipeline or one of its "
                "steps specify that code should be downloaded from a "
                "code repository "
                "(`source_files=['download_from_code_repository']`), but "
                "there is no code repository active at your current source "
                f"root `{source_utils.get_source_root()}`."
            )

        if not code_download_possible(
            deployment=deployment, code_repository=code_repository
        ):
            raise RuntimeError(
                "The `DockerSettings` of the pipeline or one of its "
                "steps specify that code can not be downloaded from the "
                "artifact store, but the build you specified requires code "
                "download. Either update your `DockerSettings` or specify a "
                "different build and try again."
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


def compute_stack_checksum(stack: StackResponse) -> str:
    """Compute a stack checksum.

    Args:
        stack: The stack for which to compute the checksum.

    Returns:
        The checksum.
    """
    hash_ = hashlib.md5()  # nosec

    # This checksum is used to see if the stack has been updated since a build
    # was created for it. We create this checksum not with specific requirements
    # as these might change with new ZenML releases, but they don't actually
    # invalidate those Docker images.
    required_integrations = sorted(
        {
            component.integration
            for components in stack.components.values()
            for component in components
            if component.integration and component.integration != "built-in"
        }
    )
    for integration in required_integrations:
        hash_.update(integration.encode())

    return hash_.hexdigest()


def should_upload_code(
    deployment: PipelineDeploymentBase,
    build: Optional[PipelineBuildResponse],
    code_reference: Optional[CodeReferenceRequest],
) -> bool:
    """Checks whether the current code should be uploaded for the deployment.

    Args:
        deployment: The deployment.
        build: The build for the deployment.
        code_reference: The code reference for the deployment.

    Returns:
        Whether the current code should be uploaded for the deployment.
    """
    if not build:
        # No build means all the code is getting executed locally, which means
        # we don't need to download any code
        # TODO: This does not apply to e.g. Databricks, figure out a solution
        # here
        return False

    for step in deployment.step_configurations.values():
        source_files = step.config.docker_settings.source_files

        if (
            code_reference
            and SourceFileMode.DOWNLOAD_FROM_CODE_REPOSITORY in source_files
        ):
            # No upload needed for this step
            continue

        if SourceFileMode.DOWNLOAD_FROM_ARTIFACT_STORE in source_files:
            break
    else:
        # Downloading code in the Docker images is prevented by Docker settings
        return False

    return True


def upload_code_if_necessary() -> str:
    """Upload code to the artifact store if necessary.

    This function computes a hash of the code to be uploaded, and if an archive
    with the same hash already exists it will not re-upload but instead return
    the path to the existing archive.

    Returns:
        The path where to archived code is uploaded.
    """
    code_archive = CodeArchive(root=source_utils.get_source_root())
    artifact_store = Client().active_stack.artifact_store

    logger.info("Archiving code...")

    with tempfile.NamedTemporaryFile(
        mode="w+b", delete=True, suffix=".tar.gz"
    ) as f:
        code_archive.write_archive(f)

        hash_ = hashlib.sha1()  # nosec

        while True:
            data = f.read(64 * 1024)
            if not data:
                break
            hash_.update(data)

        filename = f"{hash_.hexdigest()}.tar.gz"
        upload_dir = os.path.join(artifact_store.path, "code_uploads")
        fileio.makedirs(upload_dir)
        upload_path = os.path.join(upload_dir, filename)

        if not fileio.exists(upload_path):
            archive_size = string_utils.get_human_readable_filesize(
                os.path.getsize(f.name)
            )
            logger.info(
                "Uploading code to `%s` (Size: %s).", upload_path, archive_size
            )
            fileio.copy(f.name, upload_path)
            logger.info("Code upload finished.")
        else:
            logger.info(
                "Code already exists in artifact store, skipping upload."
            )

    return upload_path
