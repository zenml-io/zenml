"""Script to migrate ZenML core code to the ZenML Hub."""

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

import click
from pydantic import BaseModel

from zenml import __version__ as zenml_version
from zenml.utils.git_utils import clone_git_repository
from zenml.utils.yaml_utils import read_yaml, write_yaml


class BasePluginMigrationModel(BaseModel):
    """Base model to define the migration config entry for a plugin."""

    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class PluginMigrationModel(BasePluginMigrationModel):
    """Model to define the migration config entry for a plugin."""

    src: List[str]
    content: Optional[Dict[str, List[str]]]
    requirements: Optional[List[str]]
    logo: Optional[str]
    readme: Optional[str]


class PluginSubmitModel(BasePluginMigrationModel):
    """Model to define the submit config entry for a plugin."""

    repository_url: str
    repository_subdirectory: Optional[str] = None
    repository_branch: Optional[str] = None
    repository_commit: Optional[str] = None
    version: Optional[str] = None
    release_notes: Optional[str] = None
    logo_url: Optional[str] = None


@click.command()
@click.option(
    "input_config",
    "-i",
    type=click.Path(exists=True, dir_okay=False),
    default="src/zenml/_hub/_migration/migration_config.yaml",
)
@click.option(
    "output_config",
    "-o",
    type=click.Path(exists=False),
    default="src/zenml/_hub/_migration/submit_config.yaml",
)
@click.option(
    "repository_url",
    "-u",
    type=str,
    default="https://github.com/zenml-io/zenml-hub-plugins",
    help="The URL of the repository where the plugins should be published.",
)
@click.option(
    "repository_src_root",
    "-s",
    type=str,
    default="src/",
    help=(
        "The src root of the repository. For each new plugin, a subdirectory "
        "corresponding to the plugin name will be created in this directory."
    ),
)
@click.option(
    "commit_message",
    "-m",
    type=str,
    help=(
        "The commit message to use when committing the new plugins. If not "
        "specified, the commit message will be auto-generated."
    ),
    required=False,
)
def main(
    input_config: str,
    output_config: str,
    repository_url: str,
    repository_src_root: str,
    commit_message: Optional[str],
) -> None:
    input_config_dict = read_yaml(input_config)
    output_config_dict: List[Dict[str, Any]] = []
    if not isinstance(input_config_dict, list):
        raise ValueError("Migration config must be a list of dicts.")
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Clone plugin repo
        repo = clone_git_repository(
            url=repository_url,
            to_path=tmp_dir,
        )

        for raw_plugin_dict in input_config_dict:

            # Parse plugin input
            if not isinstance(raw_plugin_dict, dict):
                raise ValueError("Migration config must be a list of dicts.")
            plugin = PluginMigrationModel(**raw_plugin_dict)

            # Define output config entry
            repo_subdir = os.path.join(repository_src_root, plugin.name)
            logo_is_url = plugin.logo and plugin.logo.startswith("http")
            plugin_output = PluginSubmitModel(
                name=plugin.name,
                description=plugin.description,
                tags=plugin.tags,
                repository_url=repository_url,
                repository_subdirectory=repo_subdir,
                logo_url=plugin.logo if logo_is_url else None,
            )
            output_config_dict.append(plugin_output.dict(exclude_none=True))

            # Arrange and add plugin code into plugin repo
            tmp_repo_subdir = os.path.join(tmp_dir, repo_subdir)
            if os.path.exists(tmp_repo_subdir):
                shutil.rmtree(tmp_repo_subdir)
            os.makedirs(tmp_repo_subdir)
            # Create `src/` and `src/__init__.py`
            src_dir = os.path.join(tmp_repo_subdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "__init__.py"), "w") as f:
                f.write("")
            # Copy source files
            for src in plugin.src:
                dst = os.path.join(src_dir, os.path.basename(src))
                shutil.copyfile(src, dst)
            # Copy/create `README.md`
            readme_path = os.path.join(tmp_repo_subdir, "README.md")
            if plugin.readme:
                shutil.copyfile(plugin.readme, readme_path)
            else:
                with open(readme_path, "w") as f:
                    f.write(f"# {plugin.name}\n")
                    if plugin.description:
                        f.write(f"{plugin.description}\n")
            # Write requirements to `requirements.txt`
            requirements = [f"zenml>={zenml_version}"]
            if plugin.requirements:
                requirements.extend(plugin.requirements)
            reqs_path = os.path.join(tmp_repo_subdir, "requirements.txt")
            with open(reqs_path, "w") as f:
                for line in requirements:
                    f.write(f"{line}\n")
            # Copy logo to `logo.png` if it is not a URL
            if plugin.logo and not logo_is_url:
                logo_path = os.path.join(tmp_repo_subdir, "logo.png")
                shutil.copyfile(plugin.logo, logo_path)

        # Write output config
        write_yaml(output_config, output_config_dict)

        # Commit and push plugin repo
        if not commit_message:
            commit_message = f"Migrated {len(output_config_dict)} plugins."
        repo.index.add("*")
        repo.git.add(update=True)  # also add deleted/moved files
        repo.index.commit(commit_message)
        repo.remotes.origin.push()


if __name__ == "__main__":
    main()
