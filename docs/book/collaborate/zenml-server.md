---
description: Use ZenML in a Collaborative Setting with the ZenServer.
---

# The ZenML Server

Sometimes, you may need to exchange or collaborate on Stack configurations with
other developers or even just have your Stacks available on multiple machines.
While you can always zip up your Profile files or check [the local ZenStore](share-with-profiles.md)
files into version control, a more elegant solution is to have some kind of service
accessible from anywhere in your network that provides a REST API that can be
used to store and access your Stacks over the network.

The ZenServer, short for ZenML Server, is a distributed client-server ZenML
deployment scenario in which multiple ZenML clients can connect to a remote
service that provides persistent storage and acts as a central management hub
for all ZenML operations involving Stack configurations, Stack Components and
other ZenML objects.

Working with a ZenServer involves two main aspects: deploying the ZenServer
somewhere and connecting to it from your ZenML client. Keep reading to
learn more about how to configure your ZenML client to connect to a remote
ZenServer instance, or jump straight to the available ZenServer deployment
options by visiting the relevant sections:

* [run a ZenServer locally](#running-the-zenserver-locally)
* [deploy ZenServer with Docker](#deploy-the-zenserver-with-docker)
* (more to come ...)


{% hint style="info" %}
The ZenServer is still undergoing heavy development. Some features are in Alpha
state and may change in future releases. We are also working on providing more
deployment and lifecycle management options for the ZenServer that will
expand the currently supported deployment use-cases with improved scalability,
security and robustness.
{% endhint %}

## Interacting with a Remote ZenServer

The [ZenML Profile and ZenStore](share-with-profiles.md) are the main configuration
concepts behind the ZenServer architecture. To connect your ZenML client to a
remote ZenServer instance, you need the URL of the ZenServer REST API and
[a user that has been configured on the server](#zenserver-user-management).

Connecting to the ZenServer is just a matter of creating a ZenML Profile backed
by a ZenStore of type `rest` and pointing it to the ZenServer REST API URL, e.g.:

```
$ zenml profile create zenml-remote -t rest --url http://192.168.178.40:8080 --user default
Running without an active repository root.
Running with active profile: 'default' (global)
Initializing profile zenml-remote...
Profile 'zenml-remote' successfully created.

$ zenml profile set zenml-remote 
Running without an active repository root.
Running with active profile: 'devel' (global)
Active profile changed to: 'zenml-remote'
```

All ZenML pipelines executed while the ZenServer backed Profile is active will
use the Stack and Stack Component definitions stored on the server.

## Running the ZenServer Locally

The ZenServer can be deployed locally on any machine, as a means of assessing
its functionality without going through the pains of provisioning a complicated
infrastructure setup. Before we get started, we need to make sure that all the 
necessary dependencies for the ZenServer are installed. To do that, we install 
ZenML with the server extras like this:
```
pip install zenml[server]
```

Starting a local ZenServer instance can be done by typing
`zenml server up`. This will start the server as a background daemon process
accessible on your local machine, by default on port 8000:

```
$ zenml server up
Running without an active repository root.
Starting a new ZenServer local instance.
ZenServer running at 'http://127.0.0.1:8000/'.
```

The local ZenServer exposes a local REST API through which clients can access
the same data available in your active Profile. You can also specify a different
profile by passing the `--profile=$PROFILE_NAME` command-line argument, or change
the HTTP port and address on which the ZenServer is accepting requests using
`--port=$PORT` and `--ip-address=$IP_ADDRESS`.The following example creates
a new SQL profile named `zen-server` and starts a ZenServer with that profile
that listens to port 8080 on all interfaces. This is a typical use case
where you might want to expose the ZenServer to other machines in your network:

```
$ zenml server down
Shutting down the local ZenService instance.

$ zenml profile create -t sql zen-server
Running without an active repository root.
Running with active profile: 'devel' (global)
Initializing profile zen-server...
Registering default stack...
Registered stack with name 'default'.
Profile 'zen-server' successfully created.

$ zenml server up --port 8080 --ip-address 0.0.0.0 --profile zen-server
Running without an active repository root.
Starting a new ZenServer local instance.
ZenServer running at 'http://0.0.0.0:8080/'.
```

The status of the local ZenServer instance can be checked at any time using:

```
$ zenml server status
The ZenServer status is active and running at http://0.0.0.0:8080/..
```

and shut down using:

```
$ zenml server down
Shutting down the local ZenService instance.
```

To launch the ZenServer manually, without using the ZenML CLI, you can use the
`uvicorn` command line launch utility. For example, the equivalent of the
previous `zenml server up` example would be: 

```
ZENML_PROFILE_NAME=zen-server uvicorn zenml.zen_server.zen_server_api:app \
    --port 8080 --host 0.0.0.0
```

## Deploy the ZenServer with Docker

The ZenServer can be deployed as a Docker container. To persist the ZenStore
information between container restarts, the Docker container should be
configured to mount a host volume where its global configuration is kept.
The following is an example of starting a Docker container with a ZenServer
instance exposed on the local port 8080 and using a local `zenserver` folder
to persist the ZenML data between container restarts:

```
mkdir zenserver
docker run -it -d -p 8080:8000 \
    -v $PWD/zenserver:/zenserver \
    -e ZENML_CONFIG_PATH=/zenserver \
    zenmldocker/zenml \
    uvicorn zenml.zen_server.zen_server_api:app --host 0.0.0.0
```

## ZenServer User Management

All clients connecting to a ZenServer instance must use a user account. This is
currently available only as a rudimentary user management system until the
ZenServer is fully developed.

A `default` user is automatically created when the ZenServer is started. The
ZenML CLI can be used to register additional users, either directly into the
Profile that the ZenServer is running on, or remotely, from any ZenML client:

```
$ zenml profile describe
Running without an active repository root.
Running with active profile: 'zenml-remote' (global)
'zenml-remote' Profile Configuration (ACTIVE)
┏━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY     │ VALUE                      ┃
┠──────────────┼────────────────────────────┨
┃ NAME         │ zenml-remote               ┃
┠──────────────┼────────────────────────────┨
┃ STORE_URL    │ http://192.168.178.40:8080 ┃
┠──────────────┼────────────────────────────┨
┃ STORE_TYPE   │ rest                       ┃
┠──────────────┼────────────────────────────┨
┃ ACTIVE_STACK │ default                    ┃
┠──────────────┼────────────────────────────┨
┃ ACTIVE_USER  │ default                    ┃
┗━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml user list
Running without an active repository root.
Running with active profile: 'zenml-remote' (global)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━┓
┃                  ID                  │ CREATION_DATE              │ NAME    ┃
┠──────────────────────────────────────┼────────────────────────────┼─────────┨
┃ 085cb51e-37cf-4661-a8cb-ec885b218387 │ 2022-05-16 18:12:16.355773 │ default ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━┛

$ zenml user create aria
Running without an active repository root.
Running with active profile: 'zenml-remote' (global)

$ zenml user list
Running without an active repository root.
Running with active profile: 'zenml-remote' (global)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━┓
┃                  ID                  │ CREATION_DATE              │ NAME    ┃
┠──────────────────────────────────────┼────────────────────────────┼─────────┨
┃ 085cb51e-37cf-4661-a8cb-ec885b218387 │ 2022-05-16 18:12:16.355773 │ default ┃
┠──────────────────────────────────────┼────────────────────────────┼─────────┨
┃ 16dfc5da-9462-4a36-8502-15f0204501cf │ 2022-05-16 18:39:09.461282 │ aria    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━┛
```

## ZenServer API Reference

For more details on the ZenServer REST API, spin up the service and visit
`http://$SERVICE_URL/docs` to see the OpenAPI specification.
