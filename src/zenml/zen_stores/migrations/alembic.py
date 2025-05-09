#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Alembic utilities wrapper.

The Alembic class defined here acts as a wrapper around the Alembic
library that automatically configures Alembic to use the ZenML SQL store
database connection.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Column, String
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.schema import MetaData
from sqlmodel import SQLModel

from zenml.zen_stores import schemas

ZENML_ALEMBIC_START_REVISION = "alembic_start"

exclude_tables = ["sqlite_sequence"]


def include_object(
    object: Any, name: Optional[str], type_: str, *args: Any, **kwargs: Any
) -> bool:
    """Function used to exclude tables from the migration scripts.

    Args:
        object: The schema item object to check.
        name: The name of the object to check.
        type_: The type of the object to check.
        *args: Additional arguments.
        **kwargs: Additional keyword arguments.

    Returns:
        True if the object should be included, False otherwise.
    """
    return not (type_ == "table" and name in exclude_tables)


_RevIdType = Union[str, Sequence[str]]

Base = declarative_base()


class AlembicVersion(Base):  # type: ignore[valid-type,misc]
    """Alembic version table."""

    __tablename__ = "alembic_version"
    version_num = Column(String, nullable=False, primary_key=True)


class Alembic:
    """Alembic environment and migration API.

    This class provides a wrapper around the Alembic library that automatically
    configures Alembic to use the ZenML SQL store database connection.
    """

    def __init__(
        self,
        engine: Engine,
        metadata: MetaData = SQLModel.metadata,
        context: Optional[EnvironmentContext] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Alembic wrapper.

        Args:
            engine: The SQLAlchemy engine to use.
            metadata: The SQLAlchemy metadata to use.
            context: The Alembic environment context to use. If not set, a new
                context is created pointing to the ZenML migrations directory.
            **kwargs: Additional keyword arguments to pass to the Alembic
                environment context.
        """
        self.engine = engine
        self.metadata = metadata
        self.context_kwargs = kwargs

        self.config = Config()
        self.config.set_main_option(
            "script_location", str(Path(__file__).parent)
        )

        self.script_directory = ScriptDirectory.from_config(self.config)
        if context is None:
            self.environment_context = EnvironmentContext(
                self.config, self.script_directory
            )
        else:
            self.environment_context = context

    def db_is_empty(self) -> bool:
        """Check if the database is empty.

        Returns:
            True if the database is empty, False otherwise.
        """
        # Check the existence of any of the SQLModel tables
        return not self.engine.dialect.has_table(
            self.engine.connect(), schemas.StackSchema.__tablename__
        )

    def run_migrations(
        self,
        fn: Optional[Callable[[_RevIdType, MigrationContext], List[Any]]],
    ) -> None:
        """Run an online migration function in the current migration context.

        Args:
            fn: Migration function to run. If not set, the function configured
                externally by the Alembic CLI command is used.
        """
        fn_context_args: Dict[Any, Any] = {}
        if fn is not None:
            fn_context_args["fn"] = fn

        with self.engine.connect() as connection:
            # Configure the context with our metadata
            self.environment_context.configure(
                connection=connection,
                target_metadata=self.metadata,
                include_object=include_object,
                compare_type=True,
                render_as_batch=True,
                **fn_context_args,
                **self.context_kwargs,
            )

            with self.environment_context.begin_transaction():
                self.environment_context.run_migrations()

    def head_revisions(self) -> List[str]:
        """Get the head database revisions.

        Returns:
            List of head revisions.
        """
        head_revisions: List[str] = []

        def do_get_head_rev(rev: _RevIdType, context: Any) -> List[Any]:
            nonlocal head_revisions

            for r in self.script_directory.get_heads():
                if r is None:
                    continue
                head_revisions.append(r)
            return []

        self.run_migrations(do_get_head_rev)

        return head_revisions

    def current_revisions(self) -> List[str]:
        """Get the current database revisions.

        Returns:
            List of head revisions.
        """
        current_revisions: List[str] = []

        def do_get_current_rev(rev: _RevIdType, context: Any) -> List[Any]:
            nonlocal current_revisions

            # Handle rev parameter in a way that's compatible with different alembic versions
            rev_input: Any
            if isinstance(rev, str):
                rev_input = rev
            else:
                rev_input = tuple(str(r) for r in rev)

            # Get current revision(s)
            for r in self.script_directory.get_all_current(rev_input):
                if r is None:
                    continue
                current_revisions.append(r.revision)
            return []

        self.run_migrations(do_get_current_rev)

        return current_revisions

    def stamp(self, revision: str) -> None:
        """Stamp the revision table with the given revision without running any migrations.

        Args:
            revision: String revision target.
        """

        def do_stamp(rev: _RevIdType, context: Any) -> List[Any]:
            # Handle rev parameter in a way that's compatible with different alembic versions
            if isinstance(rev, str):
                return self.script_directory._stamp_revs(revision, rev)
            else:
                # Convert to tuple for compatibility
                rev_tuple = tuple(str(r) for r in rev)
                return self.script_directory._stamp_revs(revision, rev_tuple)

        self.run_migrations(do_stamp)

    def upgrade(self, revision: str = "heads") -> None:
        """Upgrade the database to a later version.

        Args:
            revision: String revision target.
        """

        def do_upgrade(rev: _RevIdType, context: Any) -> List[Any]:
            # Handle rev parameter in a way that's compatible with different alembic versions
            if isinstance(rev, str):
                return self.script_directory._upgrade_revs(revision, rev)
            else:
                if rev:
                    # Use first element or revs for compatibility
                    return self.script_directory._upgrade_revs(
                        revision, str(rev[0])
                    )
                return []

        self.run_migrations(do_upgrade)

    def downgrade(self, revision: str) -> None:
        """Revert the database to a previous version.

        Args:
            revision: String revision target.
        """

        def do_downgrade(rev: _RevIdType, context: Any) -> List[Any]:
            # Handle rev parameter in a way that's compatible with different alembic versions
            if isinstance(rev, str):
                return self.script_directory._downgrade_revs(revision, rev)
            else:
                if rev:
                    return self.script_directory._downgrade_revs(
                        revision, str(rev[0])
                    )
                return self.script_directory._downgrade_revs(revision, None)

        self.run_migrations(do_downgrade)
