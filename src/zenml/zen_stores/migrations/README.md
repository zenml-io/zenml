# How to create a migration

## How alembic works

The alembic.ini file int the repository root is used for the configuration of
alembic in general. The env.py file is the entrypoint for alembic where we tie
alembic into the SQL zen store database that ZenML is using.

If you make changes to the SQLModel schemas as a part of your development,
you'll notice the changes are not reflected in the database unless you make
an explicit alembic revision that can be used to initialize or migrate the
database. Any attempt to use ZenML with SQLModel schema changes will likely
result in SQL operational errors.

When you create an alembic revision using `alembic revision ...` the 
database instance will be compared to the state of all SQLModels under 
src/zenml/zen_stores/schemas. This means, in order for alembic to work properly
for you, make sure you have a fully instantiated version of the `develop` state
of the database, then checkout your branch with your changed schemas and run the
auto-generation to get create the diff between develop and your changes as a
migration.

The actual automatic update of the tables in handled by the 
`sql_zen_store.migrate_database()` method. This is called during instantiation 
of the `SQLZenStore`. This means, anyone using ZenML in a fresh environment 
gets all migration scripts executed in historical order to create the initial 
state of their database.

## Create a revision


1) Make sure the `store.url` of your global config points at an instance of the 
   database that represents the status-quo before your changes to the database
2) You have updated a Schema at src/zenml/zen_stores/schemas
   (e.g. adding a new column to stacks called `stack_cats`)
3) in the repository root run `alembic revision --autogenerate -m "<insert description>"`
   (e.g. `alembic revision -m "add cat column to stack"`)
   This will lead to an output like this one:
   ```shell
   Generating /home/apenner/PycharmProjects/zenml/src/zenml/alembic/versions/7b807019ae53_add_cat_column_to_stack.py ...  done
   ```
4) Go to the mentioned file and adjust the `upgrade()` and the `downgrade()` 
   functions.
   `op.add_column()`, `op.drop_column()`, `op.create_table()`, `op.drop_table()`
   are just some of the functionalities that alembic offers here.

   Note that auto generation will not work properly for column renaming, instead
   of op.rename_table or op.rename_column the column/table will be deleted and
   a new one will be created with a new name. This will lose all data that was
   on these columns. You will have to correct these errors manually. Alembic
   will also not automatically help pre-fill required fields. You will have to 
   write the appropriate code to pre-fill required columns.

5) Add the file to git and commit it.
6) The changes are automatically applied to the database the next time you 
   use the database with ZenML.