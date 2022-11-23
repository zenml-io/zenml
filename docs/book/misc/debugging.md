---
description: A guide to debug common issues.
---

# Debugging Guide
This page serves as a guide to help you find solutions to commons issues and how to debug them.

## How to post on Slack
When posting on Slack it's very useful to provide the following information (when applicable) so that anyone in 
the community can answer your questions having complete information.

### 1️⃣ System Information
Let us know relevant information about your system information.

Run the following in your terminal and copy the output to your Slack question:

`python -c "import zenml.environment; print(zenml.environment.get_system_details())"`

The output should look something like:

```python
ZenML version: 0.21.0
Install path: /home/dnth/anaconda3/envs/zenmlexample/lib/python3.8/site-packages/zenml
Python version: 3.8.13
Platform information: {'os': 'linux', 'linux_distro': 'ubuntu', 'linux_distro_like': 'debian', 'linux_distro_version': '20.04'}
Environment: native
Integrations: ['airflow', 'graphviz']
```

### 2️⃣ What happened
Tell us what were you trying to achieve? 
What did you expect to happen?
And what actually happened?

### 3️⃣ How to reproduce the error
Walk us through how to reproduce the same error you faced. 
Ideally step-by-step.

### 4️⃣ Relevant log output
Attach the relevant output to help us understand more on what happened under the hood.
Sometimes it's useful to provide more logs to give more context to the issue at hand.
See below.

## How to search Slack for answers
Go to https://open.crowd.dev/zenml and type your query in the search bar.

## How to see logs on the client and server


## How to toggle ZENML_LOGGING_VERBOSITY environment variable to show more logs
In the event that the default log is not helpful you can toggle the `ZENML_LOGGING_VERBOSITY` environment variable to change the type of logs shown.

The default value is

```shell
ZENML_LOGGING_VERBOSITY=INFO
```

You can pick other values such as `WARN`, `ERROR`, `CRITICAL`, `DEBUG` to change what's shown as logs.

See [System Environment Variable](../guidelines/system-environmental-variables.md) for more information.

## Common errors

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
We changed the limit form 4K to 65K chars, but it could still happen if you have excessively long strings in your config.

### Install ZenML on Apple Silicon without Rosetta
Our recommended, and tested approach is to install via `Rosetta`. 

But a community member recently discovered a way to install ZenML on Apple Silicon without Rosetta.
Join the conversation [here](https://open.crowd.dev/zenml/for-what-its-worth-i-was-able-to-successfully-install?q=&p=1).