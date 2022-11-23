---
description: A guide to debug common issues.
---

# Debugging Guide
This page documents a series of how-tos for efficient debugging and getting help without losing any hair.

## 🔍 How to search Slack for answers
Before posting on Slack it's a good idea to search in Slack and [GitHub issues](https://github.com/zenml-io/zenml/issues)
to see if the issue you're facing already has a solution in place. Also, check out the [Common errors](#--common-errors) section below.

We recommend that you [join our Slack channel]((https://zenml.io/meet)) and use the built-in Slack search function at the top of the page. 
Chances are you'd find your answers there.

Our current Slack plan only lets you search chat history within the past 90 days.
If you'd like to view older chats, we recommend that you head to https://open.crowd.dev/zenml and type your query in the search bar.
It should surface chats older than 90 days from our channel.
In most cases, it's not very relevant, but it's there if you'd like to peer further into the past.

If you can't find any clue, then it's time to post it on Slack.

## 🎯 How to post on Slack
When posting on Slack it's useful to provide the following information (when applicable) so that we get a 
complete picture before jumping into solutions.

### 1️⃣ System Information
Let us know relevant information about your system.
We recommend running the following in your terminal and attaching the output to your question.

`python -c "import zenml.environment; print(zenml.environment.get_system_details())"`

The output should look something like this:

```python
ZenML version: 0.21.0
Install path: /home/dnth/anaconda3/envs/zenmlexample/lib/python3.8/site-packages/zenml
Python version: 3.8.13
Platform information: {'os': 'linux', 'linux_distro': 'ubuntu', 'linux_distro_like': 'debian', 'linux_distro_version': '20.04'}
Environment: native
Integrations: ['airflow', 'graphviz']
```

System information provides more context to your issue and also eliminates the need for anyone to ask when they're trying to help.  
This increases the chances of your question getting answered and saves time for everyone.

### 2️⃣ What happened
Tell us briefly:
* What were you trying to achieve? 
* What did you expect to happen?
* What actually happened?

### 3️⃣ How to reproduce the error
Walk us through how to reproduce the same error you had step-by-step, whenever possible.

### 4️⃣ Relevant log output
Attach relevant log outputs to help us understand what happened under the hood.
Usually, the default log you see in your terminal is sufficient.

Sometimes, the default log output does not help to shed light on the issue.
In this case, it's useful to provide additional logs.
Additional logs are not shown by default, you'll have to toggle an environment variable for it.
Read the next section to find out how.

## 🔄 How to toggle `ZENML_LOGGING_VERBOSITY` environment variable to show additional logs
In the event that the default log is not helpful, you can toggle the `ZENML_LOGGING_VERBOSITY` environment variable to change the type of logs shown.

The default value is
```shell
ZENML_LOGGING_VERBOSITY=INFO
```
You can pick other values such as `WARN`, `ERROR`, `CRITICAL`, `DEBUG` to change what's shown in the logs.
See [System Environment Variable](../guidelines/system-environmental-variables.md) for more information on other environment variables that affect the behavior of ZenML.

## 📜 How to see logs on the client and server

You can see the server logs by tapping into the Kubernetes pod where the server is running, with something like this:
```shell
$ kubectl -n zenml-server-hamza get pod
NAME                            READY   STATUS    RESTARTS   AGE
zenml-server-549b46d659-5n28m   1/1     Running   0          99m
$ kubectl -n zenml-server-hamza logs zenml-server-549b46d659-5n28m
```

The logs from a healthy server should look something like this
```shell
INFO:asyncio:Syncing pipeline runs...
2022-10-19 09:09:18,195 - zenml.zen_stores.metadata_store - DEBUG - Fetched 4 steps for pipeline run '13'. (metadata_store.py:315)
2022-10-19 09:09:18,359 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
2022-10-19 09:09:18,461 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
2022-10-19 09:09:18,516 - zenml.zen_stores.metadata_store - DEBUG - Fetched 2 inputs and 2 outputs for step 'normalizer'. (metadata_store.py:427)
2022-10-19 09:09:18,606 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
```

## ❌ Common errors
This section documents frequently encountered issues and solutions among users in Slack.

### Error initializing rest store

Typically, the error presents itself as: 

```bash
RuntimeError: Error initializing rest store with URL 'http://127.0.0.1:8237': HTTPConnectionPool(host='127.0.0.1', port=8237): Max retries exceeded with url: /api/v1/login (Caused by 
NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f9abb198550>: Failed to establish a new connection: [Errno 61] Connection refused'))
```

If you restarted your machine after deploying ZenML then you have to run `zenml up` again after each restart.
Local ZenML deployments don't survive machine restarts.


### Column 'step_configuration' cannot be null

```bash
sqlalchemy.exc.IntegrityError: (pymysql.err.IntegrityError) (1048, "Column 'step_configuration' cannot be null")
```

This happens when a step configuration is too long. 
We changed the limit from 4K to 65K chars, but it could still happen if you have excessively long strings in your config.

### Install ZenML on Apple Silicon without Rosetta
Our recommended, and tested approach is to install via `Rosetta`. 

But a community member recently discovered a way to install ZenML on Apple Silicon without Rosetta.
Join the conversation [here](https://open.crowd.dev/zenml/for-what-its-worth-i-was-able-to-successfully-install?q=&p=1).