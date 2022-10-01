---
description: A guide into ZenML architecture and into concepts like providers, deployers and more!
---

Introduction to centralized tracking of metadata and to the ZenServer concept.

## Architecture

A ZenML deployment consists of two components -
- A FastAPI server tha.
- A SQL database.

The server is configured to talk to the database which hosts all the tables pertaining to your data that is being tracked through ZenML. It provides the API that the client uses, through either the `zenml` CLI or the ZenML Dashboard.

The database is decoupled from this server and can be created and managed independently of it.

// TODO SIMPLE DIAGRAM OF A SERVER AND A DATABASE SHOWING THE CLIENTS ACCESSING IT (cli and dashboard)