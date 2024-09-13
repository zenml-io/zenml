# zenml.code_repositories.git package

## Submodules

## zenml.code_repositories.git.local_git_repository_context module

Implementation of the Local git repository context.

### *class* zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext(code_repository_id: UUID, git_repo: Repo, remote_name: str)

Bases: [`LocalRepositoryContext`](zenml.code_repositories.md#zenml.code_repositories.local_repository_context.LocalRepositoryContext)

Local git repository context.

#### *classmethod* at(path: str, code_repository_id: UUID, remote_url_validation_callback: Callable[[str], bool]) → [LocalGitRepositoryContext](#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext) | None

Returns a local git repository at the given path.

Args:
: path: The path to the local git repository.
  code_repository_id: The ID of the code repository.
  remote_url_validation_callback: A callback that validates the
  <br/>
  > remote URL of the git repository.

Returns:
: A local git repository if the path is a valid git repository
  and the remote URL is valid, otherwise None.

#### *property* current_commit *: str*

The current commit.

Returns:
: The current commit sha.

#### *property* git_repo *: Repo*

The git repo.

Returns:
: The git repo object of the local git repository.

#### *property* has_local_changes *: bool*

Whether the git repo has local changes.

A repository has local changes if it is dirty or there are some commits
which have not been pushed yet.

Returns:
: True if the git repo has local changes, False otherwise.

Raises:
: RuntimeError: If the git repo is in a detached head state.

#### *property* is_dirty *: bool*

Whether the git repo is dirty.

A repository counts as dirty if it has any untracked or uncommitted
changes.

Returns:
: True if the git repo is dirty, False otherwise.

#### *property* remote *: Remote*

The git remote.

Returns:
: The remote of the git repo object of the local git repository.

#### *property* root *: str*

The root of the git repo.

Returns:
: The root of the git repo.

## Module contents

Initialization of the local git repository context.

### *class* zenml.code_repositories.git.LocalGitRepositoryContext(code_repository_id: UUID, git_repo: Repo, remote_name: str)

Bases: [`LocalRepositoryContext`](zenml.code_repositories.md#zenml.code_repositories.local_repository_context.LocalRepositoryContext)

Local git repository context.

#### *classmethod* at(path: str, code_repository_id: UUID, remote_url_validation_callback: Callable[[str], bool]) → [LocalGitRepositoryContext](#zenml.code_repositories.git.local_git_repository_context.LocalGitRepositoryContext) | None

Returns a local git repository at the given path.

Args:
: path: The path to the local git repository.
  code_repository_id: The ID of the code repository.
  remote_url_validation_callback: A callback that validates the
  <br/>
  > remote URL of the git repository.

Returns:
: A local git repository if the path is a valid git repository
  and the remote URL is valid, otherwise None.

#### *property* current_commit *: str*

The current commit.

Returns:
: The current commit sha.

#### *property* git_repo *: Repo*

The git repo.

Returns:
: The git repo object of the local git repository.

#### *property* has_local_changes *: bool*

Whether the git repo has local changes.

A repository has local changes if it is dirty or there are some commits
which have not been pushed yet.

Returns:
: True if the git repo has local changes, False otherwise.

Raises:
: RuntimeError: If the git repo is in a detached head state.

#### *property* is_dirty *: bool*

Whether the git repo is dirty.

A repository counts as dirty if it has any untracked or uncommitted
changes.

Returns:
: True if the git repo is dirty, False otherwise.

#### *property* remote *: Remote*

The git remote.

Returns:
: The remote of the git repo object of the local git repository.

#### *property* root *: str*

The root of the git repo.

Returns:
: The root of the git repo.
