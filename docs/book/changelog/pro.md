---
description: Changelog for ZenML Pro.
icon: star
layout:
  cover:
    visible: true
    size: hero
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# ZenML Pro

This document contains the release notes for ZenML Pro (Cloud API & Control Plane).

### 0.12.19

**What's Changed**

* General maintenance and release preparation.

### 0.12.18

**What's Changed**

* General maintenance and release preparation.

### 0.12.17

**New Features & Improvements**

* **Lambda Function Updates:** Updated Python version for Lambda functions.
* **Vault Secret Store:** Support for new Hashicorp Vault secret store auth method settings.
* **Authentication:**
    * Allow API keys and Personal Access Tokens (PATs) to be used as bearer tokens.
    * Add configurable expiration to API keys.
* **Codespaces:** Add JupyterLab support to Codespaces.

### 0.12.16

**What's Changed**

* General maintenance and release preparation.

### 0.12.15

**Fixes**

* Filter long user avatar URLs at source for older workspace versions (<= 0.90.0).

### 0.12.14

**What's Changed**

* General maintenance and release preparation.

### 0.12.12

**New Features**

* **Service Accounts:** Allow invitations by service accounts.

### 0.12.11

**New Features**

* **Service Accounts:** Allow service accounts to invite users.

### 0.12.10

**New Features**

* **Service Accounts:** Allow service accounts to authenticate to workspaces.
* **Testing:** Add team resource member test.
* **Updates:** Bump default workspace version and run template resources.

### 0.12.9

**What's Changed**

* General maintenance and release preparation.

### 0.12.8

**New Features**

* **Workspaces:** Allow name changes for workspaces.

### 0.12.7

**New Features**

* **RBAC:** Enable schedule RBAC.
* **Roles:** Add team viewer default role.

### 0.12.6

**New Features**

* **Service Accounts:**
    * Allow specifying initial service account role.
    * Add new fields to service account schema and models.
* **Workspaces:**
    * Prevent regular users from creating/updating workspaces to older ZenML releases.
    * Prevent regular users from updating the onboarded flag.
* **Fixes:** Service account fixes and membership filtering.

### 0.12.5

**New Features**

* **Onboarding:** User onboarded flag implementation.
* **Dependencies:** Bump `aiohttp`.

### 0.12.3

**Improvements**

* **Codespaces:** Delete codespaces when cleaning up expired tenants.
* **Workspaces:** Bump workspace default version.

### 0.12.2

**New Features**

* **Codespaces:**
    * Add `zenml_active_project_id` to CodespaceCreate model.
    * Delete Codespaces on Workspace Delete.
* **Storage:** Implement workspace storage usage count, limiting, and cleanup.

### 0.12.0

**New Features**

* **Codespaces:** Introducing Codespaces to Cloud API.
* **Workspaces:** Provision shared workspace bucket with Terraform.
* **RBAC:** More permissions handling for internal users.
* **Members:** Include empty teams in members lists.

