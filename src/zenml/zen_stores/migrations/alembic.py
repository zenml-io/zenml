from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Sequence, Union

from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import MetaData

from sqlmodel import SQLModel

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory

from zenml.zen_stores import schemas

if TYPE_CHECKING:
    from alembic.runtime.migration import StampStep

exclude_tables = [
    "Event",
    "EventPath",
    "Attribution",
    "Association",
    "MLMDEnv",
    "ExecutionProperty",
    "Execution",
    "Artifact",
    "ArtifactProperty",
    "TypeProperty",
    "ParentType",
    "ParentContext",
    "Context",
    "Type",
    "ContextProperty",
    "sqlite_sequence",
]


def include_object(object, name, type_, *args, **kwargs):
    return not (type_ == "table" and name in exclude_tables)


_RevIdType = Union[str, Sequence[str]]


class Alembic:
    """Alembic environment and migration API."""

    def __init__(
        self,
        engine: Engine,
        metadata: MetaData = SQLModel.metadata,
        **kwargs: Any,
    ) -> None:
        self.engine = engine
        self.metadata = metadata
        self.context_kwargs = kwargs

        # # add logging handler if not configured
        # console_handler = logging.StreamHandler(sys.stderr)
        # console_handler.formatter = logging.Formatter(
        #     fmt="%(levelname)-5.5s [%(name)s] %(message)s", datefmt="%H:%M:%S"
        # )

        # sqlalchemy_logger = logging.getLogger("sqlalchemy")
        # alembic_logger = logging.getLogger("alembic")

        # if not sqlalchemy_logger.hasHandlers():
        #     sqlalchemy_logger.setLevel(logging.WARNING)
        #     sqlalchemy_logger.addHandler(console_handler)

        # # alembic adds a null handler, remove it
        # if len(alembic_logger.handlers) == 1 and isinstance(
        #     alembic_logger.handlers[0], logging.NullHandler
        # ):
        #     alembic_logger.removeHandler(alembic_logger.handlers[0])

        # if not alembic_logger.hasHandlers():
        #     alembic_logger.setLevel(logging.INFO)
        #     alembic_logger.addHandler(console_handler)

        self.config = Config()
        self.config.set_main_option(
            "script_location", str(Path(__file__).parent)
        )
        self.config.set_main_option(
            "version_locations", str(Path(__file__).parent / "versions")
        )

        self.script_directory = ScriptDirectory.from_config(self.config)
        self.environment_context = EnvironmentContext(
            self.config, self.script_directory
        )

    def _run_migrations(
        self, fn: Callable[[_RevIdType, EnvironmentContext], List["StampStep"]]
    ):
        """Run an online migration function in the current migration context."""
        with self.engine.connect() as connection:
            self.environment_context.configure(
                connection=connection,
                target_metadata=self.metadata,
                include_object=include_object,
                compare_type=True,
                render_as_batch=True,
                fn=fn,
                **self.context_kwargs,
            )

            with self.environment_context.begin_transaction():
                self.environment_context.run_migrations()

    def stamp(self, revision: str):
        """Stamp the revision table with the given revision without running any migrations.

        Args:
            revision: String revision target.
        """

        def do_stamp(
            rev: _RevIdType, context: EnvironmentContext
        ) -> List["StampStep"]:
            return self.script_directory._stamp_revs(revision, rev)

        self._run_migrations(do_stamp)

    def upgrade(self, revision: str = "heads") -> None:
        """Upgrade the database to a later version.

        Args:
            revision: String revision target.
        """

        def do_upgrade(
            rev: _RevIdType, context: EnvironmentContext
        ) -> List["StampStep"]:
            return self.script_directory._upgrade_revs(revision, rev)

        self._run_migrations(do_upgrade)

    def downgrade(self, revision: str) -> None:
        """Revert the database to a previous version.

        Args:
            revision: String revision target.
        """

        def do_downgrade(
            rev: _RevIdType, context: EnvironmentContext
        ) -> List["StampStep"]:
            return self.script_directory._downgrade_revs(revision, rev)

        self._run_migrations(do_downgrade)
