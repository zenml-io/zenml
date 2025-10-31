---
icon: lock
description: >-
  Learn how to link your own secrets store backend to your ZenML Pro workspace.
---

# Secrets Stores

The secrets you configure in your ZenML Pro workspaces are by default stored in the same database as your other workspace resources. However, you have the option to link your own backend to your workspace and store the secrets in your own infrastructure. This functionality is powered by the same [ZenML Secrets Store functionality](https://docs.zenml.io/deploying-zenml/deploying-zenml/secret-management) that is available in ZenML OSS and several options are available for you to choose from: AWS Secrets Manager, GCP Secret Manager, Azure Key Vault and HashiCorp Vault.

## How to configure a secrets store

This operation has two main stages:

1. first, you prepare the authentication credentials and necessary permissions for the secrets store. This varies depending on the secrets store backend and the authentication method you want to use (see following sections for more details).
2. then, you communicate these credentials to the ZenML Pro support team, who will update your workspace to use the new secrets store and also migrate all your existing secrets in the process.

## AWS Secrets Manager

The authentication used by the AWS secrets store is built on the [ZenML Service Connector](https://docs.zenml.io/stacks/service-connectors/auth-management) of the same type as the secrets store. This means that you can use any of the [authentication methods supported by the Service Connector](https://docs.zenml.io/stacks/service-connectors/connector-types/aws-service-connector#authentication-methods) to authenticate with the secrets store.

The recommended authentication method documented here is to use the [implicit authentication method](https://docs.zenml.io/stacks/service-connectors/connector-types/aws-service-connector#implicit-authentication), because this doesn't need any sensitive credentials to be exchanged with the ZenML Pro support team.

The process is as follows:

1. Identify the AWS IAM role of your ZenML Pro workspace. Every ZenML Pro workspace is associated with a particular AWS IAM role that bears all the AWS permissions granted to the workspace. The ARN of this role is formed as follows: `arn:aws:iam::715803424590:role/zenml-<workspace-uuid>`. For example, if your workspace UUID is `123e4567-e89b-12d3-a456-426614174000`, the ARN of the role is `arn:aws:iam::715803424590:role/zenml-123e4567-e89b-12d3-a456-426614174000`.

2. Create an AWS IAM role in your AWS account that will be assumed by the ZenML Pro workspace role:

  * use the following trust relationship to allow the ZenML Pro workspace role to assume the new role:

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::715803424590:role/zenml-<workspace-uuid>"
          }
        }
      ]
    }
    ```

   * attach the following custom IAM policy to the new role to allow it to access the AWS Secrets Manager service:

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "secretsmanager:CreateSecret",
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "secretsmanager:PutSecretValue",
            "secretsmanager:UpdateSecret",
            "secretsmanager:TagResource",
            "secretsmanager:DeleteSecret"
          ],
          "Resource": "arn:aws:secretsmanager:<AWS-region>:<AWS-account-id>:secret:zenml/*"
        }
      ]
    }
    ```

3. Contact the ZenML Pro support team to update your ZenML Pro workspace to use the new secrets store. You will need to provide the ARN of the new role you created in step 2 and the region where the AWS Secrets Manager service is located. After your workspace is updated, you will see the following changes in the workspace configuration:

```json
{
  "id": "...",
  "name": "...",
  "zenml_service": {
    "configuration": {
      "version": "...",
      "secrets_store": {
        "type": "aws",
        "settings": {
          "auth_method": "implicit",
          "auth_config": {
            "region": "<AWS-region>",
            "role_arn": "arn:aws:iam::<AWS-account-id>:role/<IAM-role-name>"
          }
        }
      }
    }
  }
}
```

Here is an example Terraform code to create the new role and attach the custom policy:

```terraform
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "zenml_pro_workspace_role" {
  name = "zenml-${var.workspace_uuid}"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Principal = {
            AWS = "arn:aws:iam::715803424590:role/zenml-${var.workspace_uuid}"
          }
        }
      ]
    }
  )
}

resource "aws_iam_role_policy" "zenml_pro_workspace_policy" {
  name = "zenml-${var.workspace_uuid}"
  role = aws_iam_role.zenml_pro_workspace_role.id
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:CreateSecret",
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "secretsmanager:PutSecretValue",
            "secretsmanager:UpdateSecret",
            "secretsmanager:TagResource",
            "secretsmanager:DeleteSecret"
          ]
          Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:zenml/*"
        }
      ]
    }
  )
}

output "zenml_pro_secrets_store_role_arn" {
  value = aws_iam_role.zenml_pro_secrets_store_role.arn
}

output "zenml_pro_secrets_store_region" {
  value = data.aws_region.current.name
}
```

If you choose a different authentication method, your will need to provide different credentials. See the [AWS Secrets Manager](https://docs.zenml.io/stacks/service-connectors/connector-types/aws-service-connector#authentication-methods) documentation on the available authentication methods and their configuration options for more details.

## HashiCorp Vault

The HashiCorp Vault secrets store supports the following authentication methods:

* [Token authentication](https://python-hvac.org/en/stable/usage/auth_methods/token.html) - authentication using a static token
* [App Role authentication](https://python-hvac.org/en/stable/usage/auth_methods/approle.html) - authentication using a Vault App Role (app role ID and secret ID)
* [AWS authentication](https://python-hvac.org/en/stable/usage/auth_methods/aws.html) - implicit authentication using an AWS IAM role (IAM role ARN)

The recommended authentication method documented here is to use the implicit AWS authentication, because this doesn't need any sensitive credentials to be exchanged with the ZenML Pro support team.

The process is as follows:

1. Identify the AWS IAM role of your ZenML Pro workspace. Every ZenML Pro workspace is associated with a particular AWS IAM role that bears all the AWS permissions granted to the workspace. The ARN of this role is formed as follows: `arn:aws:iam::715803424590:role/zenml-<workspace-uuid>`. For example, if your workspace UUID is `123e4567-e89b-12d3-a456-426614174000`, the ARN of the role is `arn:aws:iam::715803424590:role/zenml-123e4567-e89b-12d3-a456-426614174000`.

2. Enable the AWS authentication method for your HashiCorp Vault:

```shell
vault auth enable aws
```

3. Enable the AWS authentication method for your HashiCorp Vault and configure an AWS role to use for authentication, e.g.:


```shell
vault auth enable aws

vault write auth/aws/config/client \
  iam_server_id_header_value="<workspace-uuid>" \
  sts_region="eu-central-1"

vault write auth/aws/role/zenml-<workspace-uuid> \
  auth_type=iam \
  bound_iam_principal_arn=arn:aws:iam::715803424590:role/zenml-<workspace-uuid> \
  resolve_aws_unique_ids=false \
  policies="zenml-<workspace-uuid>" \
  ttl=1h max_ttl=24h
```

A few points to note:

* use the IAM role ARN of your ZenML Pro workspace as the bound IAM principal ARN.
* it's recommended to use a header value to further secure the authentication process. Use a value that is unique to your workspace.
* configuring `resolve_aws_unique_ids` to `false` is required for the authentication to work.
* you can point to a custom policy to further restrict the permissions of the authenticated role to a particular mount point.

4. Contact the ZenML Pro support team to update your ZenML Pro workspace to use the new secrets store. You will need to provide the following information:

* the URL of the HashiCorp Vault server
* the name of the AWS Hashicorp Vault role you created in step 2 (e.g. `zenml-<workspace-uuid>`)
* the header value you used for the authentication process (e.g. `<workspace-uuid>`)
* the namespace of the HashiCorp Vault server (if applicable)
* the mount point to use (if applicable)

After your workspace is updated, you will see the following changes in the workspace configuration:

```json
{
  "id": "...",
  "name": "...",
  "zenml_service": {
    "configuration": {
      "version": "...",
      "secrets_store": {
        "type": "hashicorp",
        "settings": {
          "auth_method": "aws",
          "auth_config": {
            "vault_addr": "https://vault.example.com",
            "vault_namespace": "zenml",
            "mount_point": "secrets-<workspace-uuid>",
            "aws_role": "zenml-<workspace-uuid>",
            "aws_header_value": "<workspace-uuid>"
          }
        }
      }
    }
  }
}
```
