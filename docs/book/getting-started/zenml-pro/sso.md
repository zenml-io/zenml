---
description: Configure Single Sign-On (SSO) authentication for ZenML Pro self-hosted deployments.
layout:
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

# Single Sign-On (SSO)

This guide covers Single Sign-On (SSO) configuration for ZenML Pro self-hosted deployments. SSO allows users to authenticate through an external identity provider instead of using local accounts with password authentication.

{% hint style="info" %}
SSO configuration is only applicable to [the fully self-hosted scenario](self-hosted-deployment.md). [The hybrid scenario](hybrid-deployment.md) uses the ZenML Pro SaaS SSO for authentication.
{% endhint %}

## Overview

By default, the ZenML Pro control plane uses local accounts with password authentication. Enabling SSO provides several benefits:

- **Centralized user management**: Users are managed in your identity provider, not in ZenML Pro
- **Enhanced security**: Leverage your organization's existing authentication policies (MFA, password policies, etc.)
- **Simplified access**: Users authenticate with credentials they already know
- **Automated provisioning**: ZenML Pro user accounts are created automatically on first login

You can start with local accounts and enable SSO later without losing existing data. SSO and password authentication can also be enabled simultaneously during a transition period.

## SSO Prerequisites

### Supported Identity Providers

Any OIDC-compatible identity provider can be used, including:

| Provider Type | Examples |
|---------------|----------|
| Cloud identity services | Google Workspace, Microsoft Entra ID (Azure AD), Okta, Auth0 |
| Self-hosted solutions | Keycloak, Authentik, Dex, Gluu |
| Enterprise directories | ADFS, Ping Identity, OneLogin |

### Identity Provider Requirements

Your identity provider must meet the following specifications:

| Requirement | Description |
|-------------|-------------|
| OAuth 2.0 authorization code flow | Must support the standard authorization code grant |
| JWT ID token | Must issue JWT ID tokens during the authorization code flow |
| Required scopes | `openid`, `email`, `profile` |
| OpenID configuration endpoint | Must expose `/.well-known/openid-configuration` at a URL reachable by the ZenML Pro control plane |
| JWKS | Must implement JSON Web Key Set for signing ID tokens |
| Logout endpoint (optional) | If supported, enables single logout functionality |

### ZenML Pro Client Configuration in the Identity Provider

When registering ZenML Pro as an OIDC client in your identity provider, configure the following:

| Setting | Value |
|---------|-------|
| Redirect URI | `https://<zenml-ui-url>/api/auth/callback` |
| Post-logout redirect URI | `https://<zenml-ui-url>/api/auth/logout-complete` (if logout is supported) |
| Allowed scopes | `openid`, `email`, `profile` |
| Client type | Confidential (requires client secret) |

After registration, your identity provider will issue a **client ID** and **client secret** that you will need when configuring ZenML Pro, in addition to the URL to the OpenID configuration endpoint (`/.well-known/openid-configuration`).

### Information to Collect

Before configuring SSO, gather the following information from your identity provider:

| Parameter | Value |
|-----------|-------|
| Identity provider | `_______________` (e.g., Okta, Azure AD, Keycloak) |
| OIDC discovery URL | `_______________` (e.g., `https://idp.example.com/.well-known/openid-configuration`) |
| Client ID | `_______________` |
| Client secret | `_______________` |
| Redirect URI (configured in IdP) | `https://<web-ui-url>/api/auth/callback` |
| Post-logout redirect URI (if applicable) | `https://<web-ui-url>/api/auth/logout-complete` |
| IDP logout URI to call (if applicable) | `https://<idp-url>/v2/logout` |

## Configuring SSO

SSO is configured differently depending on your deployment method. Refer to the deployment guide for your chosen infrastructure:

- [Control Plane Kubernetes Deployment](deploy-control-plane-k8s.md) — SSO configuration via Helm values

## Migrating from Password Authentication to SSO

If you have an existing ZenML Pro deployment using local accounts with password authentication, you can migrate to SSO authentication while preserving all existing resources and their ownership. This section describes the recommended migration process.

### Migration Overview

The migration process involves running both authentication methods simultaneously during a transition period, then disabling password authentication once all users have migrated to SSO. During this period:

- Existing local users continue to have access to their resources
- New SSO users can be invited and granted permissions
- Resource ownership can be transferred if needed

### Step 1: Enable SSO While Keeping Password Authentication

Update your ZenML Pro control plane configuration to enable SSO authentication while keeping password authentication enabled. This allows both authentication methods to work simultaneously.

{% hint style="warning" %}
Do not disable password authentication at this stage. Doing so would lock out all existing local user accounts immediately.
{% endhint %}

The specific configuration depends on your deployment method. Refer to your deployment guide for details on how to enable SSO.

### Step 2: Log In with a Local User Account

After enabling SSO, log in to the ZenML Pro UI using an existing local user account that has administrative privileges (e.g., a super-user account or an organization owner).

This account will be used to invite SSO users and grant them the necessary permissions to manage the organization and its resources.

### Step 3: Invite SSO Users to Organizations

While logged in with the local user account, invite the SSO users who will take over management of the organization:

1. Navigate to **Organization Settings** → **Members**
2. Click **Invite Member**
3. Enter the email address of the SSO user (this should match the email address in your identity provider)
4. Assign appropriate roles (e.g., Organization Owner, Organization Admin)
5. Repeat for all SSO users who need access

{% hint style="info" %}
The invited users don't need to exist in ZenML Pro yet. Their accounts will be created automatically when they first log in via SSO and accept the invitation.
{% endhint %}

### Step 4: SSO Users Accept Invitations

Each invited SSO user should:

1. Access the ZenML Pro UI
2. Log in using the SSO authentication flow (click "Sign in with SSO" or similar)
3. After authentication, accept any pending organization invitations

Once an SSO user accepts an invitation, they have full access to the organization according to their assigned roles.

### Step 5: Transfer Resource Ownership (Optional)

If local users own resources that should be transferred to SSO users, you can update the ownership through the UI or API. This step is optional—resources owned by local users remain accessible to organization members based on their roles even after disabling password authentication.

{% hint style="info" %}
Resource ownership primarily affects who can delete or transfer resources. Organization members with appropriate roles can still view and use resources owned by other users within the organization.
{% endhint %}

### Step 6: Disable Password Authentication

Once all SSO users have been invited, have accepted their invitations, and have verified they can access all necessary resources, you can disable password authentication.

{% hint style="warning" %}
Disabling password authentication will immediately lock out all local user accounts. Ensure all users who need access have successfully authenticated via SSO before proceeding.
{% endhint %}

Update your ZenML Pro control plane configuration to disable password authentication. The specific configuration depends on your deployment method.

After disabling password authentication:

- Local user accounts can no longer log in
- Resources owned by local users remain in the system and are accessible to organization members
- The admin account used for initial setup is also disabled
- Only SSO authentication is available

### Rollback Procedure

If you need to re-enable password authentication after disabling it:

1. Update your ZenML Pro control plane configuration to re-enable password authentication
2. Local user accounts will be able to log in again with their original passwords

{% hint style="info" %}
Local user account passwords are preserved in the database even when password authentication is disabled. Re-enabling password authentication restores access without requiring password resets.
{% endhint %}

## Troubleshooting

### Common SSO Issues

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| "Invalid redirect URI" error | Redirect URI in ZenML Pro doesn't match the one configured in your IdP | Verify the redirect URI matches exactly, including the protocol (https) |
| Users can't log in after SSO is enabled | OIDC discovery URL is not reachable from the ZenML Pro control plane | Check network connectivity and firewall rules |
| User email doesn't match invitation | Email claim in the ID token differs from the invited email | Verify the email address format in your IdP matches what was invited |
| SSO login works but user has no access | User hasn't accepted organization invitation | User should check for pending invitations after logging in |

### Verifying SSO Configuration

Before disabling password authentication, verify that SSO is working correctly:

1. Open an incognito/private browser window
2. Navigate to the ZenML Pro UI
3. Attempt to log in using SSO
4. Verify you can access the expected organizations and resources

## Related Resources

- [Self-hosted Deployment Overview](self-hosted-deployment.md)
- [Roles & Permissions](roles.md)
- [Organizations](organization.md)
