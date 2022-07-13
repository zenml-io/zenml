---
description: Centralized ZenML Stack Management with ZenStores.
---

# Share Stacks and Profiles via ZenStores

The ZenML **Store** (or **ZenStore**) is a low-level concept used to represent the
particular driver used to store and retrieve the data that is managed through a
ZenML Profile. The ZenStore concept is not directly represented in the CLI
commands, but it is reflected in the Profile configuration and can be
manipulated by passing advanced parameters to the `zenml profile create` CLI
command. The particular ZenStore driver type and configuration used for a
Profile can be viewed by bringing up the detailed Profile description (note the
store type and URL):

```
$ zenml profile describe
Running without an active repository root.
Running with active profile: 'default' (global)
          'default' Profile Configuration (ACTIVE)           
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                       ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ NAME         │ default                                     ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ STORE_URL    │ file:///home/zenml/.config/profiles/default ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ STORE_TYPE   │ local                                       ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ ACTIVE_STACK │ default                                     ┃
┠──────────────┼─────────────────────────────────────────────┨
┃ ACTIVE_USER  │ default                                     ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Different ZenStore types can be used to implement different deployment use-cases
with regards to where the ZenML managed data is stored and how and where it can
be accessed:

* [the `local` ZenStore](#local-zenml-store) stores Profile data in YAML files
on your local filesystem. This is the default ZenStore type and is suitable for
local development and testing. Local Profiles can also be shared between
multiple users even hosts by using some form of source version control or shared
filesystem.
* [the `sql` ZenStore](#sql-zenml-store) driver is based on [SQLAlchemy](https://www.sqlalchemy.org/)
and can interface with any SQL database service, local or remote, to store the
Profile data in a SQL database. The SQL driver is an easy way to extend ZenML to
accommodate multiple users working from multiple hosts.
* the `rest` ZenStore is a special type of store that connects via a REST API to
a remote ZenServer instance. This use-case is applicable to larger teams and
organizations that need to deploy ZenML as a dedicated service providing
centralized management of Stacks, Pipelines and other ZenML concepts. Please
consult the [ZenServer](./zenml-server.md) documentation dedicated to this
deployment model.

### Local ZenML Store

By default, newly created Profiles use the `local` ZenStore driver that stores
the Profile data on the local filesystem, in
[the global configuration directory](../developer-guide/repo-and-config.md),
as a collection of YAML files.

The YAML representation makes it suitable to commit Stack configurations and
all other information stored in the Profile into a version control system such
as Git, where they can be versioned and shared with other users.

To use a custom location for a Profile, point the ZenStore URL to a directory
on your local filesystem. For example:

```
$ zenml profile create git_store --url /tmp/zenml/.zenprofile
Running with active profile: 'default' (local)
Initializing profile git...
Registering default stack...
Registered stack component with type 'orchestrator' and name 'default'.
Registered stack component with type 'metadata_store' and name 'default'.
Registered stack component with type 'artifact_store' and name 'default'.
Registered stack with name 'default'.
Profile 'git_store' successfully created.

$ zenml profile set git_store
Running with active profile: 'default' (local)
Active profile changed to: 'git_store'

$ zenml profile describe
Running with active profile: 'git_store' (local)
  'git_store' Profile Configuration (ACTIVE)   
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                  ┃
┠──────────────┼────────────────────────┨
┃ NAME         │ git_store              ┃
┠──────────────┼────────────────────────┨
┃ STORE_URL    │ /tmp/zenml/.zenprofile ┃
┠──────────────┼────────────────────────┨
┃ STORE_TYPE   │ local                  ┃
┠──────────────┼────────────────────────┨
┃ ACTIVE_STACK │ default                ┃
┠──────────────┼────────────────────────┨
┃ ACTIVE_USER  │ default                ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Assuming the `/tmp/zenml` location used above is part of a local git
clone that is regularly synchronized with a remote server, replicating the
same Profile on another machine is straightforward: if the URL points to a
location where a Profile already exists, the Profile information is
loaded from the existing YAML files:

```
user@another_machine:/tmp$ git clone <git-repo-location> zenml
user@another_machine:/tmp$ cd zenml
user@another_machine:/tmp/zenml$

user@another_machine:/tmp$ zenml profile create git-clone --url ./.zenprofile
Running with active profile: 'git' (local)
Initializing profile git-clone...
Profile 'git-clone' successfully created.
```

As alternatives to version control, a Profile could be shared by using a
distributed filesystem (e.g. NFS) or by regularly syncing the folder with a
remote central repository using some other means. However, a better solution
of sharing Profiles across multiple machines is be to use
[the SQL ZenStore driver](#sql-zenml-store) to store the Profile data in
a SQL database, or to manage ZenML data through a centralized
[ZenServer](./zenml-server.md) instance.

### SQL ZenML Store

The SQL ZenStore type uses [SQLAlchemy](https://www.sqlalchemy.org/) to
store Profile data in a [local SQLite database file](#local-sqlite-profile),
on [a remote MySQL server](#mysql-profile) or any SQL compatible database system
for that matter. The URL value passed during the Profile creation controls the
type, location and other parameters for the SQL database connection. To explore
the full range of configuration options, consult the
[SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/dialects/index.html).

#### Local SQLite Profile

The simplest form of SQL-based Profile uses a SQLite file located in
[the global configuration directory](../developer-guide/repo-and-config.md):

```
$ zenml profile create sqlite_profile -t sql
Running without an active repository root.
Running with active profile: 'default' (global)
Initializing profile sqlite_profile...
Registering default stack...
Registered stack with name 'default'.
Profile 'sqlite_profile' successfully created.

$ zenml profile set sqlite_profile
Running without an active repository root.
Running with active profile: 'zenml' (global)
Active profile changed to: 'sqlite_profile'

$ zenml profile describe
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
                    'sqlite_profile' Profile Configuration (ACTIVE)                     
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                                                 ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ NAME         │ sqlite_profile                                                        ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ STORE_URL    │ sqlite:////home/stefan/.config/zenml/profiles/sqlite_profile/zenml.db ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ STORE_TYPE   │ sql                                                                   ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ ACTIVE_STACK │ default                                                               ┃
┠──────────────┼───────────────────────────────────────────────────────────────────────┨
┃ ACTIVE_USER  │ default                                                               ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The location of the SQLite database can be customized during profile creation:

```
$ zenml profile create custom_sqlite -t sql --url=sqlite:////tmp/zenml/zenml_profile.db
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
Initializing profile custom_sqlite...
Registering default stack...
Registered stack with name 'default'.
Profile 'custom_sqlite' successfully created.

$ zenml profile set custom_sqlite
Running without an active repository root.
Running with active profile: 'sqlite_profile' (global)
Active profile changed to: 'custom_sqlite'

$ zenml profile describe
Running without an active repository root.
Running with active profile: 'custom_sqlite' (global)
     'custom_sqlite' Profile Configuration (ACTIVE)     
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                                 ┃
┠──────────────┼───────────────────────────────────────┨
┃ NAME         │ custom_sqlite                         ┃
┠──────────────┼───────────────────────────────────────┨
┃ STORE_URL    │ sqlite:////tmp/zenml/zenml_profile.db ┃
┠──────────────┼───────────────────────────────────────┨
┃ STORE_TYPE   │ sql                                   ┃
┠──────────────┼───────────────────────────────────────┨
┃ ACTIVE_STACK │ default                               ┃
┠──────────────┼───────────────────────────────────────┨
┃ ACTIVE_USER  │ default                               ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### MySQL Profile

To connect the ZenML Profile to an existing MySQL database, some additional
configuration is required on the MySQL server to create a user and database:

```
mysql -u root
GRANT ALL PRIVILEGES ON *.* TO 'zenml'@'%' IDENTIFIED BY 'password';

mysql -u zenml -p
CREATE DATABASE zenml;
```

Then, on the client machine, some additional packages need to be installed.
Check [the SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/dialects/mysql.html)
for the various MySQL drivers that are supported and how to install and use
them. The following is an example of using the [mysqlclient](https://docs.sqlalchemy.org/en/14/dialects/mysql.html#module-sqlalchemy.dialects.mysql.mysqldb)
driver for SQLAlchemy on an Ubuntu OS. Depending on your choice of driver and
host OS, your experience may vary:

```
sudo apt install libmysqlclient-dev
pip install mysqlclient
```

Finally, the command to create a new Profile would look like this:

```
$ zenml profile create --store-type sql --url "mysql://zenml:password@10.11.12.13/zenml" mysql_profile
```
