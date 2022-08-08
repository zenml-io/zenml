---
description: How to reference secrets when configuring stack components
---

Some of the components in your stack require you to configure them with 
sensitive information like passwords or tokens so they can connect to the 
underlying infrastructure. Secret references allow you to configure these components in
a secure way by not specifying the value directly but instead referencing a secret.
To reference a secret in any string attribute of your stack components, simply specify
the attribute value using the following syntax:
```shell
${ secret_name.secret_key }
```

For example:
```shell
zenml metadata-store register secure_metadata_store \
    --flavor=mysql \
    --username='${ mysql_secret.username }' \
    --password='${ mysql_secret.password }' \
    ...
```

When using components with secret references in your stack, you need to make sure
that the stack contains a [secrets manager](../../mlops-stacks/secrets-managers/secrets-managers.md)
and all the referenced secrets exist in this secrets manager. To make this process easier, you can
use the following CLI command to interactively register all secrets for a stack:
```shell
zenml stack register-secrets [<STACK_NAME>]
```

