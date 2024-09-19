# zenml.code_repositories package

## Subpackages

* [zenml.code_repositories.git package](zenml.code_repositories.git.md)
  * [Submodules](zenml.code_repositories.git.md#submodules)
  * [zenml.code_repositories.git.local_git_repository_context module](zenml.code_repositories.git.md#module-zenml.code_repositories.git.local_git_repository_context)
    * [`LocalGitRepositoryContext`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext)
      * [`LocalGitRepositoryContext.at()`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.at)
      * [`LocalGitRepositoryContext.current_commit`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.current_commit)
      * [`LocalGitRepositoryContext.git_repo`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.git_repo)
      * [`LocalGitRepositoryContext.has_local_changes`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.has_local_changes)
      * [`LocalGitRepositoryContext.is_dirty`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.is_dirty)
      * [`LocalGitRepositoryContext.remote`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.remote)
      * [`LocalGitRepositoryContext.root`](zenml.code_repositories.git.md#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext.root)
  * [Module contents](zenml.code_repositories.git.md#module-zenml.code_repositories.git)
    * [`LocalGitRepositoryContext`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext)
      * [`LocalGitRepositoryContext.at()`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.at)
      * [`LocalGitRepositoryContext.current_commit`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.current_commit)
      * [`LocalGitRepositoryContext.git_repo`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.git_repo)
      * [`LocalGitRepositoryContext.has_local_changes`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.has_local_changes)
      * [`LocalGitRepositoryContext.is_dirty`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.is_dirty)
      * [`LocalGitRepositoryContext.remote`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.remote)
      * [`LocalGitRepositoryContext.root`](zenml.code_repositories.git.md#zenml.code_repositories.git.LocalGitRepositoryContext.root)

## Submodules

## zenml.code_repositories.base_code_repository module

Base class for code repositories.

### *class* zenml.code_repositories.base_code_repository.BaseCodeRepository(id: UUID, config: Dict[str, Any])

Bases: `ABC`

Base class for code repositories.

Code repositories are used to connect to a remote code repository and
store information about the repository, such as the URL, the owner,
the repository name, and the host. They also provide methods to
download files from the repository when a pipeline is run remotely.

#### *property* config *: [BaseCodeRepositoryConfig](#zenml.code_repositories.base_code_repository.BaseCodeRepositoryConfig)*

Config class for Code Repository.

Returns:
: The config class.

#### *abstract* download_files(commit: str, directory: str, repo_sub_directory: str | None) → None

Downloads files from the code repository to a local directory.

Args:
: commit: The commit hash to download files from.
  directory: The directory to download files to.
  repo_sub_directory: The subdirectory in the repository to
  <br/>
  > download files from.

Raises:
: RuntimeError: If the download fails.

#### *classmethod* from_model(model: [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)) → [BaseCodeRepository](#zenml.code_repositories.base_code_repository.BaseCodeRepository)

Loads a code repository from a model.

Args:
: model: The CodeRepositoryResponseModel to load from.

Returns:
: The loaded code repository object.

#### *abstract* get_local_context(path: str) → [LocalRepositoryContext](#zenml.code_repositories.local_repository_context.LocalRepositoryContext) | None

Gets a local repository context from a path.

Args:
: path: The path to the local repository.

Returns:
: The local repository context object.

#### *property* id *: UUID*

ID of the code repository.

Returns:
: The ID of the code repository.

#### *abstract* login() → None

Logs into the code repository.

This method is called when the code repository is initialized.
It should be used to authenticate with the code repository.

Raises:
: RuntimeError: If the login fails.

#### *property* requirements *: Set[str]*

Set of PyPI requirements for the repository.

Returns:
: A set of PyPI requirements for the repository.

### *class* zenml.code_repositories.base_code_repository.BaseCodeRepositoryConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`SecretReferenceMixin`](zenml.config.md#zenml.config.secret_reference_mixin.SecretReferenceMixin), `ABC`

Base config for code repositories.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.code_repositories.local_repository_context module

Base class for local code repository contexts.

### *class* zenml.code_repositories.local_repository_context.LocalRepositoryContext(code_repository_id: UUID)

Bases: `ABC`

Base class for local repository contexts.

This class is used to represent a local repository. It is used
to track the current state of the repository and to provide
information about the repository, such as the root path, the current
commit, and whether the repository is dirty.

#### *property* code_repository_id *: UUID*

Returns the ID of the code repository.

Returns:
: The ID of the code repository.

#### *abstract property* current_commit *: str*

Returns the current commit of the local repository.

Returns:
: The current commit of the local repository.

#### *abstract property* has_local_changes *: bool*

Returns whether the local repository has local changes.

A repository has local changes if it is dirty or there are some commits
which have not been pushed yet.

Returns:
: Whether the local repository has local changes.

#### *abstract property* is_dirty *: bool*

Returns whether the local repository is dirty.

A repository counts as dirty if it has any untracked or uncommitted
changes.

Returns:
: Whether the local repository is dirty.

#### *abstract property* root *: str*

Returns the root path of the local repository.

Returns:
: The root path of the local repository.

## Module contents

Initialization of the ZenML code repository base abstraction.

### *class* zenml.code_repositories.BaseCodeRepository(id: UUID, config: Dict[str, Any])

Bases: `ABC`

Base class for code repositories.

Code repositories are used to connect to a remote code repository and
store information about the repository, such as the URL, the owner,
the repository name, and the host. They also provide methods to
download files from the repository when a pipeline is run remotely.

#### *property* config *: [BaseCodeRepositoryConfig](#zenml.code_repositories.base_code_repository.BaseCodeRepositoryConfig)*

Config class for Code Repository.

Returns:
: The config class.

#### *abstract* download_files(commit: str, directory: str, repo_sub_directory: str | None) → None

Downloads files from the code repository to a local directory.

Args:
: commit: The commit hash to download files from.
  directory: The directory to download files to.
  repo_sub_directory: The subdirectory in the repository to
  <br/>
  > download files from.

Raises:
: RuntimeError: If the download fails.

#### *classmethod* from_model(model: [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)) → [BaseCodeRepository](#zenml.code_repositories.base_code_repository.BaseCodeRepository)

Loads a code repository from a model.

Args:
: model: The CodeRepositoryResponseModel to load from.

Returns:
: The loaded code repository object.

#### *abstract* get_local_context(path: str) → [LocalRepositoryContext](#zenml.code_repositories.LocalRepositoryContext) | None

Gets a local repository context from a path.

Args:
: path: The path to the local repository.

Returns:
: The local repository context object.

#### *property* id *: UUID*

ID of the code repository.

Returns:
: The ID of the code repository.

#### *abstract* login() → None

Logs into the code repository.

This method is called when the code repository is initialized.
It should be used to authenticate with the code repository.

Raises:
: RuntimeError: If the login fails.

#### *property* requirements *: Set[str]*

Set of PyPI requirements for the repository.

Returns:
: A set of PyPI requirements for the repository.

### *class* zenml.code_repositories.LocalRepositoryContext(code_repository_id: UUID)

Bases: `ABC`

Base class for local repository contexts.

This class is used to represent a local repository. It is used
to track the current state of the repository and to provide
information about the repository, such as the root path, the current
commit, and whether the repository is dirty.

#### *property* code_repository_id *: UUID*

Returns the ID of the code repository.

Returns:
: The ID of the code repository.

#### *abstract property* current_commit *: str*

Returns the current commit of the local repository.

Returns:
: The current commit of the local repository.

#### *abstract property* has_local_changes *: bool*

Returns whether the local repository has local changes.

A repository has local changes if it is dirty or there are some commits
which have not been pushed yet.

Returns:
: Whether the local repository has local changes.

#### *abstract property* is_dirty *: bool*

Returns whether the local repository is dirty.

A repository counts as dirty if it has any untracked or uncommitted
changes.

Returns:
: Whether the local repository is dirty.

#### *abstract property* root *: str*

Returns the root path of the local repository.

Returns:
: The root path of the local repository.
