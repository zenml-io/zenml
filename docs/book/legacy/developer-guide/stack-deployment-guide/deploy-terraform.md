---
description: Deploy stack recipes without having to install ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


As mentioned in the [overview](./overview.md), you can still use the recipe without having using the `zenml stack recipe` CLI commands or even without installing ZenML. Since each recipe is a group of Terraform modules, you can simply use the Terraform CLI to perform apply and destroy operations.

## Create the stack

1. 🎨 Customize your deployment by editing the default values in the `locals.tf` file.

2. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

3. Initialize Terraform modules and download provider definitions.
    ```
    terraform init
    ```

4. Apply the recipe.
    ```
    terraform apply
    ```

## Getting the outputs

For outputs that are sensitive, you'll see that they are not shown directly on the logs. To view the full list of outputs, run the following command:

```
terraform output
```

To view individual sensitive outputs, use the following format. Here, the metadata password is being obtained.

```
terraform output metadata-db-password
```

## Deleting resources

1. 🗑️ Run the destroy function to clean up all resources.
    ```
    terraform destroy
    ```
