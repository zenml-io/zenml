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

* General maintenance and release preparation (#462).

### 0.12.18

**What's Changed**

* General maintenance and release preparation (#460).

### 0.12.17

**New Features & Improvements**

* **Lambda Function Updates:** Updated Python version for Lambda functions (#450).
* **Vault Secret Store:** Support for new Hashicorp Vault secret store auth method settings (#452).
* **Authentication:**
    * Allow API keys and Personal Access Tokens (PATs) to be used as bearer tokens (#453).
    * Add configurable expiration to API keys (#454).
* **Codespaces:** Add JupyterLab support to Codespaces (#455).

### 0.12.16

**What's Changed**

* General maintenance and release preparation (#449).

### 0.12.15

**Fixes**

* Filter long user avatar URLs at source for older workspace versions (<= 0.90.0) (#447).

### 0.12.14

**What's Changed**

* General maintenance and release preparation (#446).

### 0.12.12

**New Features**

* **Service Accounts:** Allow invitations by service accounts (#440).

### 0.12.11

**New Features**

* **Service Accounts:** Allow service accounts to invite users (#438).

### 0.12.10

**New Features**

* **Service Accounts:** Allow service accounts to authenticate to workspaces (#433).
* **Testing:** Add team resource member test (#430).
* **Updates:** Bump default workspace version (#434) and run template resources (#435).

### 0.12.9

**What's Changed**

* General maintenance and release preparation (#431).

### 0.12.8

**New Features**

* **Workspaces:** Allow name changes for workspaces (#428).

### 0.12.7

**New Features**

* **RBAC:** Enable schedule RBAC (#423).
* **Roles:** Add team viewer default role (#426).

### 0.12.6

**New Features**

* **Service Accounts:**
    * Allow specifying initial service account role (#416).
    * Add new fields to service account schema and models (#419).
* **Workspaces:**
    * Prevent regular users from creating/updating workspaces to older ZenML releases (#421).
    * Prevent regular users from updating the onboarded flag (#422).
* **Fixes:** Service account fixes and membership filtering (#424).

### 0.12.5

**New Features**

* **Onboarding:** User onboarded flag implementation (#414).
* **Dependencies:** Bump `aiohttp` (#418).

### 0.12.3

**Improvements**

* **Codespaces:** Delete codespaces when cleaning up expired tenants (#403).
* **Workspaces:** Bump workspace default version (#407).

### 0.12.2

**New Features**

* **Codespaces:**
    * Add `zenml_active_project_id` to CodespaceCreate model (#400).
    * Delete Codespaces on Workspace Delete (#401).
* **Storage:** Implement workspace storage usage count, limiting, and cleanup (#402).

### 0.12.0

**New Features**

* **Codespaces:** Introducing Codespaces to Cloud API (#380).
* **Workspaces:** Provision shared workspace bucket with Terraform (#396).
* **RBAC:** More permissions handling for internal users (#392).
* **Members:** Include empty teams in members lists (#397).
