---
description: Changelog for ZenML Pro.
icon: clock-rotate-left
---

# ZenML Pro Changelog

Stay up to date with the latest features, improvements, and fixes in ZenML Pro.

## 0.12.19

See what's new and improved in version 0.12.19.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/31.jpg" alt="ZenML Pro 0.12.19"></figure></p>

**General Updates**

* Maintenance and release preparation
* Continued improvements to platform stability

### What's Changed

* General maintenance and release preparation (#462)

***

## 0.12.18

See what's new and improved in version 0.12.18.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/32.jpg" alt="ZenML Pro 0.12.18"></figure></p>

**General Updates**

* Maintenance and release preparation
* Continued improvements to platform stability

### What's Changed

* General maintenance and release preparation (#460)

***

## 0.12.17

See what's new and improved in version 0.12.17.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/20.jpg" alt="ZenML Pro 0.12.17"></figure></p>

**Lambda Function Updates**

* Updated Python version for Lambda functions
* Improved performance and compatibility

[PR #450](https://github.com/zenml-io/zenml-cloud-api/pull/450)

**Authentication Enhancements**

* API keys and PATs can be used as bearer tokens
* Configurable expiration for API keys

[PR #453](https://github.com/zenml-io/zenml-cloud-api/pull/453) | [PR #454](https://github.com/zenml-io/zenml-cloud-api/pull/454)

**Vault Secret Store**

* Support for new Hashicorp Vault secret store auth method settings
* Enhanced security options

[PR #452](https://github.com/zenml-io/zenml-cloud-api/pull/452)

**Codespaces**

* JupyterLab support added to Codespaces
* Enhanced development environment

[PR #455](https://github.com/zenml-io/zenml-cloud-api/pull/455)

### Improved

* Lambda function Python version updates (#450)
* Enhanced authentication flexibility (#453, #454)
* Better Codespace development experience (#455)

***

## 0.12.16

See what's new and improved in version 0.12.16.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/33.jpg" alt="ZenML Pro 0.12.16"></figure></p>

**General Updates**

* Maintenance and release preparation
* Continued improvements to platform stability

### What's Changed

* General maintenance and release preparation (#449)

***

## 0.12.15

See what's new and improved in version 0.12.15.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/34.jpg" alt="ZenML Pro 0.12.15"></figure></p>

**Bug Fixes**

* Filter long user avatar URLs at source for older workspace versions
* Improved compatibility with legacy workspace versions

### Fixed

* Filter long user avatar URLs at source for older workspace versions (<= 0.90.0) (#447)

***

## 0.12.14

See what's new and improved in version 0.12.14.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/35.jpg" alt="ZenML Pro 0.12.14"></figure></p>

**General Updates**

* Maintenance and release preparation
* Continued improvements to platform stability

### What's Changed

* General maintenance and release preparation (#446)

***

## 0.12.12

See what's new and improved in version 0.12.12.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/22.jpg" alt="ZenML Pro 0.12.12"></figure></p>

**Service Account Enhancements**

* Service accounts can now invite users
* Improved automation capabilities

[PR #440](https://github.com/zenml-io/zenml-cloud-api/pull/440)

***

## 0.12.11

See what's new and improved in version 0.12.11.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/23.jpg" alt="ZenML Pro 0.12.11"></figure></p>

**Service Account Features**

* Service accounts can invite users
* Enhanced collaboration capabilities

[PR #438](https://github.com/zenml-io/zenml-cloud-api/pull/438)

***

## 0.12.10

See what's new and improved in version 0.12.10.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/24.jpg" alt="ZenML Pro 0.12.10"></figure></p>

**Service Account Authentication**

* Service accounts can authenticate to workspaces
* Better team resource management

[PR #433](https://github.com/zenml-io/zenml-cloud-api/pull/433)

### Improved

* Service account authentication to workspaces (#433)
* Team resource member testing (#430)
* Default workspace version updates (#434)
* Run template resource improvements (#435)

***

## 0.12.9

See what's new and improved in version 0.12.9.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/36.jpg" alt="ZenML Pro 0.12.9"></figure></p>

**General Updates**

* Maintenance and release preparation
* Continued improvements to platform stability

### What's Changed

* General maintenance and release preparation (#431)

***

## 0.12.8

See what's new and improved in version 0.12.8.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/25.jpg" alt="ZenML Pro 0.12.8"></figure></p>

**Workspace Features**

* Workspaces can now be renamed
* Improved workspace management

[PR #428](https://github.com/zenml-io/zenml-cloud-api/pull/428)

***

## 0.12.7

See what's new and improved in version 0.12.7.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/26.jpg" alt="ZenML Pro 0.12.7"></figure></p>

**RBAC Enhancements**

* Schedule RBAC enabled
* Team viewer default role added

[PR #423](https://github.com/zenml-io/zenml-cloud-api/pull/423) | [PR #426](https://github.com/zenml-io/zenml-cloud-api/pull/426)

***

## 0.12.6

See what's new and improved in version 0.12.6.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/27.jpg" alt="ZenML Pro 0.12.6"></figure></p>

**Service Account Improvements**

* Specify initial service account role
* New fields in service account schema and models

[PR #416](https://github.com/zenml-io/zenml-cloud-api/pull/416) | [PR #419](https://github.com/zenml-io/zenml-cloud-api/pull/419)

**Workspace Controls**

* Prevent users from creating/updating workspaces to older ZenML releases
* Prevent users from updating the onboarded flag

[PR #421](https://github.com/zenml-io/zenml-cloud-api/pull/421) | [PR #422](https://github.com/zenml-io/zenml-cloud-api/pull/422)

### Improved

* Service account role configuration (#416)
* Enhanced service account schema (#419)
* Better workspace version control (#421, #422)

### Fixed

* Service account fixes and membership filtering (#424)

***

## 0.12.5

See what's new and improved in version 0.12.5.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/28.jpg" alt="ZenML Pro 0.12.5"></figure></p>

**Onboarding**

* User onboarded flag implementation
* Better user experience tracking

[PR #414](https://github.com/zenml-io/zenml-cloud-api/pull/414)

### Improved

* User onboarding tracking (#414)
* Dependency updates (#418)

***

## 0.12.3

See what's new and improved in version 0.12.3.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/29.jpg" alt="ZenML Pro 0.12.3"></figure></p>

**Codespaces**

* Delete codespaces when cleaning up expired tenants
* Improved resource management

[PR #403](https://github.com/zenml-io/zenml-cloud-api/pull/403)

### Improved

* Codespace cleanup automation (#403)
* Workspace default version updates (#407)

***

## 0.12.2

See what's new and improved in version 0.12.2.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/30.jpg" alt="ZenML Pro 0.12.2"></figure></p>

**Codespaces**

* Add `zenml_active_project_id` to CodespaceCreate model
* Delete Codespaces on Workspace Delete

[PR #400](https://github.com/zenml-io/zenml-cloud-api/pull/400) | [PR #401](https://github.com/zenml-io/zenml-cloud-api/pull/401)

**Workspace Storage**

* Workspace storage usage count, limiting, and cleanup
* Better resource management

[PR #402](https://github.com/zenml-io/zenml-cloud-api/pull/402)

***

## 0.12.0

See what's new and improved in version 0.12.0.

<p align="left"><figure><img src="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/projects/21.jpg" alt="ZenML Pro 0.12.0"></figure></p>

**Codespaces**

* Introducing Codespaces to Cloud API
* Enhanced development environment support

[PR #380](https://github.com/zenml-io/zenml-cloud-api/pull/380)

**Workspace Storage**

* Workspace storage usage count, limiting, and cleanup
* Better resource management

[PR #402](https://github.com/zenml-io/zenml-cloud-api/pull/402)

**Infrastructure**

* Provision shared workspace bucket with Terraform
* Improved infrastructure as code support

[PR #396](https://github.com/zenml-io/zenml-cloud-api/pull/396)

**RBAC**

* More permissions handling for internal users
* Enhanced access control

[PR #392](https://github.com/zenml-io/zenml-cloud-api/pull/392)

### Improved

* Codespaces integration (#380)
* Workspace storage management (#402)
* Terraform infrastructure support (#396)
* RBAC improvements (#392)
* Team member management (#397)
