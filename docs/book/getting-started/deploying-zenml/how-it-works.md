---
description: A guide into ZenML architecture and into concepts like providers, deployers and more!
---

ZenML is designed to lives at the interface between 
all the ingredients to your machine learning development environment. As such 
there is a lot of configuration and metadata to keep track of. This means that
ZenML does not only give users an easy-to-use abstraction layer on top of their 
infrastructure and environments, but also needs to act as a collaborative 
metadata store.

## How Configurations and Pipeline Runs are tracked

ZenML relies on a SQLAlchemy compatible database to store all its data. The 
location and type of this database can be freely chosen by the user. By default,
a SQLite database is used (see [Scenario 1](#scenario-1-local-sqlite))

ZenML can also be deployed with an HTTP interface between the users machine 
and the database. This is also the interface used by the browser dashboard.
Especially in multi-user settings this is the recommended configuration
scenario.

## Scenario 1: Direct interaction with Local SQLite

This is likely the first experience that users will run into. Simply pip install 
zenml and dive right in without having to worry about a thing. Your stacks,
stack components and pipeline runs all are stored on a sqlite database at
`(~/.config/zenml/local_stores/default_zen_store/zenml.db)`. The ZenML client 
creates and directly connects to this db. You don't need to worry about a thing.

![ZenML on SQLite](../../assets/getting_started/Scenario1.png)

* If the user wants to be fancy, find out how to configure a different location,
or different db altogether [here]()

## Scenario 2: Local Deployment of the HTTP server

* All calls go through HTTP endpoints
* Allows running the Dashboard
* Data still stored in the same location as Scenario 1
* ZenMl natively supports running either in a Daemon Thread or Docker Image 
-> Find out more [here]()


![ZenML on with Local HTTP Server](../../assets/getting_started/Scenario2.png)

## Scenario 3: Remote Deployment of the HTTP server and Database

* Explain why user might want this (collaboration, remote orchestration)
* Explain who or what will access this deployment (user machine, dashboard,
orchestrator, step operator, ..., this is relevant as these advanced users need 
to make decisions early on) 
* Explain how the Database and HTTP Server are decoupled and can be created and
managed independently
* Link to section that explains this more


![ZenML on with Remote HTTP Server](../../assets/getting_started/Scenario3.1.png)
![ZenML on with Remote HTTP Server - Collaboration](../../assets/getting_started/Scenario3.2.png)
