---
description: >-
  Organization trusted domains in ZenML Pro — user visibility, invitations,
  SSO, and how operators configure them.
icon: globe
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

# Trusted domains

Trusted domains are an optional ZenML Pro control-plane feature. Each organization can store a list of DNS hostnames (for example `example.com` and `example.org`) that ZenML treats as trusted email domains for that organization. The setting affects:

- Who can appear when you search for ZenML users (for example when inviting someone to an organization or workspace)
- How organization invitations complete when the invitee signs in with Single Sign-On (SSO), including whether an invitation can finish automatically after OAuth login instead of requiring an explicit accept step

Trusted domains work together with email addresses on ZenML user accounts and with SSO/OAuth sign-in. They do not replace [roles and permissions](roles.md); they constrain discovery and change invitation completion rules where the product applies them.

## User visibility and discovery

ZenML Pro surfaces a global user listing for flows such as picking someone to invite. Which ZenML accounts you see in that listing depends on your account, your organization memberships, and how trusted domains are configured.

When trusted domains are set on organizations you belong to, visibility can expand beyond a minimal baseline: accounts whose email addresses match those domains (including typical subdomain forms of a registered domain, such as addresses under `eng.example.com` when `example.com` is trusted) may become discoverable where policy allows.

Across multiple organizations, effective discovery follows the combined trusted-domain policy associated with your memberships (you effectively see the union of what those policies allow), subject to deployment rules and server-side limits.

{% hint style="info" %}
Trusted domains adjust discovery and invitation behavior; they are not a substitute for granting roles. A user must still receive the right organization or workspace roles to use resources.
{% endhint %}

When trusted domains are not configured for your organizations, user discovery falls back to the default behavior for your deployment (ZenML-managed cloud versus self-hosted control plane). Exact defaults can differ by deployment type.

## Invitations and SSO

Trusted domains change organization invitations, not workspace-only flows by themselves:

- If an invitation is created for an email address that matches the target organization's trusted domains at invitation creation time, ZenML may record that invitation as eligible for automatic completion when the invitee later signs in with SSO/OAuth.
- If the address does not match those domains, the invitation behaves like a classic invitation: the invitee accepts or declines through the usual UI or API flows.

Automatic completion still respects subscription limits and other organization constraints when the invitation would add a member.

Trusted domains do not remove invitations as a mechanism; they change how in-domain invitations can complete when SSO is used.

## Deployments without SSO

If users authenticate with only local passwords and SSO is not used (typical for some self-hosted setups), trusted domains do not apply the same invitation auto-completion and discovery rules in the same way. Plan on [SSO](sso.md) if you want automatic completion for colleagues whose email domains match your organization.

## Configuring trusted domains

### ZenML-managed ZenML Pro

Changing trusted domains requires operator-level access (super-users on the ZenML-managed service). Customers cannot set this alone in the UI.

**ZenML-managed deployments:** To enable or change trusted domains for your organization, [contact ZenML support](https://zenml.io/slack) or your account contact.

### Self-hosted control plane

**Self-hosted deployments:** Accounts with super-user privileges can configure trusted domains through the ZenML Pro API on organization create and update operations using the `trusted_domains` field:

- Sending a list replaces the entire configured set
- Omitting the field leaves the current list unchanged
- Sending an empty list clears trusted domains

Use your deployment's OpenAPI UI or the published [ZenML Pro API](https://cloudapi.zenml.io/) reference for request bodies and validation rules.

## Related documentation

- [Organizations](organization.md) — billing, members, and organization settings in the UI
- [Roles & Permissions](roles.md) — who can do what after someone is a member
- [Single Sign-On (SSO)](sso.md) — configuring OIDC and SSO on self-hosted control planes
- [User Accounts](user-accounts.md) — account types on self-hosted deployments