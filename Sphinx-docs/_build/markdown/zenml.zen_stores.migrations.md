# zenml.zen_stores.migrations package

## Submodules

## zenml.zen_stores.migrations.alembic module

Alembic utilities wrapper.

The Alembic class defined here acts as a wrapper around the Alembic
library that automatically configures Alembic to use the ZenML SQL store
database connection.

### *class* zenml.zen_stores.migrations.alembic.Alembic(engine: Engine, metadata: MetaData = MetaData(), context: EnvironmentContext | None = None, \*\*kwargs: Any)

Bases: `object`

Alembic environment and migration API.

This class provides a wrapper around the Alembic library that automatically
configures Alembic to use the ZenML SQL store database connection.

#### current_revisions() → List[str]

Get the current database revisions.

Returns:
: List of head revisions.

#### db_is_empty() → bool

Check if the database is empty.

Returns:
: True if the database is empty, False otherwise.

#### downgrade(revision: str) → None

Revert the database to a previous version.

Args:
: revision: String revision target.

#### head_revisions() → List[str]

Get the head database revisions.

Returns:
: List of head revisions.

#### run_migrations(fn: Callable[[str | Sequence[str], MigrationContext], List[Any]] | None) → None

Run an online migration function in the current migration context.

Args:
: fn: Migration function to run. If not set, the function configured
  : externally by the Alembic CLI command is used.

#### stamp(revision: str) → None

Stamp the revision table with the given revision without running any migrations.

Args:
: revision: String revision target.

#### upgrade(revision: str = 'heads') → None

Upgrade the database to a later version.

Args:
: revision: String revision target.

### *class* zenml.zen_stores.migrations.alembic.AlembicVersion(\*\*kwargs)

Bases: `Base`

Alembic version table.

#### version_num

### zenml.zen_stores.migrations.alembic.include_object(object: Any, name: str, type_: str, \*args: Any, \*\*kwargs: Any) → bool

Function used to exclude tables from the migration scripts.

Args:
: object: The schema item object to check.
  name: The name of the object to check.
  <br/>
  ```
  type_
  ```
  <br/>
  : The type of the object to check.
  <br/>
  ```
  *
  ```
  <br/>
  args: Additional arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: True if the object should be included, False otherwise.

## zenml.zen_stores.migrations.utils module

ZenML database migration, backup and recovery utilities.

### *class* zenml.zen_stores.migrations.utils.MigrationUtils(\*, url: URL, connect_args: Dict[str, Any], engine_args: Dict[str, Any])

Bases: `BaseModel`

Utilities for database migration, backup and recovery.

#### backup_database_to_db(backup_db_name: str) → None

Backup the database to a backup database.

Args:
: backup_db_name: Backup database name to backup to.

#### backup_database_to_file(dump_file: str) → None

Backup the database to a file.

This method dumps the entire database into a JSON file. Instead of
using a SQL dump, we use a proprietary JSON dump because:

> * it is (mostly) not dependent on the SQL dialect or database version
> * it is safer with respect to SQL injection attacks
> * it is easier to read and debug

The JSON file contains a list of JSON objects instead of a single JSON
object, because it allows for buffered reading and writing of the file
and thus reduces the memory footprint. Each JSON object can contain
either schema or data information about a single table. For tables with
a large amount of data, the data is split into multiple JSON objects
with the first object always containing the schema.

The format of the dump is as depicted in the following example:

```
``
```

```
`
```

json
{

> “table”: “table1”,
> “create_stmt”: “CREATE TABLE table1 (id INTEGER NOT NULL, “

> > “name VARCHAR(255), PRIMARY KEY (id))”

### }

> “table”: “table1”,
> “data”: [
> {

> > “id”: 1,
> > “name”: “foo”

> },
> {

> > “id”: 1,
> > “name”: “bar”

> ]

### }

> “table”: “table1”,
> “data”: [
> {

> > “id”: 101,
> > “name”: “fee”

> },
> {

> > “id”: 102,
> > “name”: “bee”

> ]

#### }

Args:
: dump_file: The path to the dump file.

#### backup_database_to_memory() → List[Dict[str, Any]]

Backup the database in memory.

Returns:
: The in-memory representation of the database backup.

Raises:
: RuntimeError: If the database cannot be backed up successfully.

#### backup_database_to_storage(store_db_info: Callable[[Dict[str, Any]], None]) → None

Backup the database to a storage location.

Backup the database to an abstract storage location. The storage
location is specified by a function that is called repeatedly to
store the database information. The function is called with a single
argument, which is a dictionary containing either the table schema or
table data. The dictionary contains the following keys:

> * table: The name of the table.
> * create_stmt: The table creation statement.
> * data: A list of rows in the table.

Args:
: store_db_info: The function to call to store the database
  : information.

#### connect_args *: Dict[str, Any]*

#### create_database(database: str | None = None, drop: bool = False) → None

Creates a mysql database.

Args:
: database: The name of the database to create. If not set, the
  : database name from the configuration will be used.
  <br/>
  drop: Whether to drop the database if it already exists.

#### create_engine(database: str | None = None) → Engine

Get the SQLAlchemy engine for a database.

Args:
: database: The name of the database. If not set, a master engine
  : will be returned.

Returns:
: The SQLAlchemy engine.

#### database_exists(database: str | None = None) → bool

Check if a database exists.

Args:
: database: The name of the database to check. If not set, the
  : database name from the configuration will be used.

Returns:
: Whether the database exists.

Raises:
: OperationalError: If connecting to the database failed.

#### drop_database(database: str | None = None) → None

Drops a mysql database.

Args:
: database: The name of the database to drop. If not set, the
  : database name from the configuration will be used.

#### *property* engine *: Engine*

The SQLAlchemy engine.

Returns:
: The SQLAlchemy engine.

#### engine_args *: Dict[str, Any]*

#### *classmethod* is_mysql_missing_database_error(error: OperationalError) → bool

Checks if the given error is due to a missing database.

Args:
: error: The error to check.

Returns:
: If the error because the MySQL database doesn’t exist.

#### *property* master_engine *: Engine*

The SQLAlchemy engine for the master database.

Returns:
: The SQLAlchemy engine for the master database.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'arbitrary_types_allowed': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'connect_args': FieldInfo(annotation=Dict[str, Any], required=True), 'engine_args': FieldInfo(annotation=Dict[str, Any], required=True), 'url': FieldInfo(annotation=URL, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### restore_database_from_db(backup_db_name: str) → None

Restore the database from the backup database.

Args:
: backup_db_name: Backup database name to restore from.

Raises:
: RuntimeError: If the backup database does not exist.

#### restore_database_from_file(dump_file: str) → None

Restore the database from a backup dump file.

See the documentation of the backup_database_to_file method for
details on the format of the dump file.

Args:
: dump_file: The path to the dump file.

Raises:
: RuntimeError: If the database cannot be restored successfully.

#### restore_database_from_memory(db_dump: List[Dict[str, Any]]) → None

Restore the database from an in-memory backup.

Args:
: db_dump: The in-memory database backup to restore from generated
  : by the backup_database_to_memory method.

Raises:
: RuntimeError: If the database cannot be restored successfully.

#### restore_database_from_storage(load_db_info: Callable[[], Generator[Dict[str, Any], None, None]]) → None

Restore the database from a backup storage location.

Restores the database from an abstract storage location. The storage
location is specified by a function that is called repeatedly to
load the database information from the external storage chunk by chunk.
The function must yield a dictionary containing either the table schema
or table data. The dictionary contains the following keys:

> * table: The name of the table.
> * create_stmt: The table creation statement.
> * data: A list of rows in the table.

The function must return None when there is no more data to load.

Args:
: load_db_info: The function to call to load the database
  : information.

#### url *: URL*

## Module contents

Alembic database migration utilities.
