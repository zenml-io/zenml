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

## How to see logs on the client and server

## How to toggle ZENML_LOGGING_VERBOSITY env variable to show more logs

## Common errors