---
description: Manage your ZenML stacks with Terraform
---

# Manage stacks with Terraform

Terraform is a powerful tool for managing infrastructure as code, and is by far the
most popular IaC tool. Many companies already have existing Terraform setups,
and it is often desirable to integrate ZenML with this setup.

We already got a glimpse on how to [deploy a cloud stack with Terraform](../stack-deployment/deploy-a-cloud-stack-with-terraform.md)
using existing Terraform modules that are maintained by the ZenML team. While this
is a great solution for quickly getting started, it might not always be suitable.
For example, you might want to manage different types of stacks for different
environments (e.g. `prod`, `staging`, `dev`) or you might want to manage your
stacks in a version control system.

For these use cases, you can learn. This is what we will cover in this section.