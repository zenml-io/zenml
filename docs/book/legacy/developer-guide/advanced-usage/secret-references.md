---
description: How to reference secrets when configuring stack components
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Some of the components in your stack require you to configure them with 
sensitive information like passwords or tokens so they can connect to the 
underlying infrastructure. Secret references allow you to configure these components in
a secure way by not specifying the value directly but instead referencing a secret.
To reference a secret in any string attribute of your stack components, simply specify
the attribute value using the following syntax:
```shell
{{<SECRET_NAME>.<SECRET_KEY>}}
```

For example:
```shell
zenml metadata-store register secure_metadata_store \
    --flavor=mysql \
    --username='{{mysql_secret.username}}' \
    --password='{{mysql_secret.password}}' \
    ...
```

## Register missing secrets for your stack

When using components with secret references in your stack, you need to make sure
that the stack contains a [secrets manager](../../mlops-stacks/secrets-managers/secrets-managers.md)
and all the referenced secrets exist in this secrets manager. To make this process easier, you can
use the following CLI command to interactively register all secrets for a stack:
```shell
zenml stack register-secrets [<STACK_NAME>]
```

## Secret validation

Before running a pipeline, ZenML will validate your stack and make sure that all secrets
and keys referenced in your stack components exist. This helps us fail early so your 
pipeline doesn't fail after running for some time due to some missing secret.

This validation by default needs to fetch and read every secret to make sure that
both the secret and the specified key-value pair exist. This can take quite some time and
might fail if you don't have the permissions to read secrets.
You can use the environment variable `ZENML_SECRET_VALIDATION_LEVEL` to disable or 
control the degree to which ZenML validates your secrets:
* Setting it to `NONE` disables any validation.
* Setting it to `SECRET_EXISTS` only validates the existence of secrets. This might be useful
if the machine you're running on only has permissions to list secrets but not actually read
their values.
* Setting it to `SECRET_AND_KEY_EXISTS` (the default) validates both the secret existence as
well as the existence of the exact key-value pair.
