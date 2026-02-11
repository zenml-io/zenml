#!/usr/bin/env python3
"""
ZenML Pro User Synchronization Script

This script synchronizes users from an external identity provider (IdP)
with ZenML Pro. It demonstrates how to:
- Fetch users from an IdP (example uses a mock IdP client)
- Map IdP groups to ZenML Pro organizations, teams, and roles
- Use invitations as placeholders for users who haven't logged in yet
- Create, update, and deactivate users via the ZenML Pro API

Key concepts:
- Invitations act as temporary placeholders for user accounts before users
  log in and accept them. You can assign roles and team memberships to
  invitations just as you would to user accounts. When the user logs in via
  SSO and accepts the invitation, the permissions linked to the invitation
  are automatically transferred to the user account.
- Organization membership is established by assigning organization-level
  roles (not a dedicated membership endpoint).
- Teams are organization-scoped but have their own top-level API endpoints.

Prerequisites:
- requests library: pip install requests
- A ZenML Pro service account API key with appropriate permissions
- Network access to both the IdP and ZenML Pro API

Usage:
    export ZENML_PRO_API_URL="https://zenml-pro.example.com/api/v1"
    export ZENML_PRO_API_KEY="your-service-account-api-key"
    export IDP_URL="https://your-idp.example.com"
    export IDP_TOKEN="your-idp-admin-token"
    python sync_sso_users.py
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IdPUser:
    """Represents a user from the identity provider."""

    email: str
    name: str
    groups: list[str] = field(default_factory=list)
    is_active: bool = True


class IdPClient:
    """Client for fetching users from your identity provider.

    Replace this with your actual IdP client implementation.
    Examples: Okta SDK, Microsoft Graph API, Keycloak Admin API, etc.
    """

    def __init__(self, idp_url: str, idp_token: str):
        self.idp_url = idp_url
        self.idp_token = idp_token

    def list_users(self) -> list[IdPUser]:
        """Fetch all users from the IdP.

        Replace with actual IdP API calls.
        """
        # Example: Okta
        # response = requests.get(
        #     f"{self.idp_url}/api/v1/users",
        #     headers={"Authorization": f"SSWS {self.idp_token}"}
        # )
        # return [self._parse_okta_user(u) for u in response.json()]

        # Placeholder - replace with your IdP implementation
        raise NotImplementedError("Implement IdP user fetching")


class ZenMLProClient:
    """Client for interacting with the ZenML Pro API.

    This client provides methods for:
    - User management (list, update, deactivate)
    - Organization management (list, list roles, list members)
    - Invitation management (create, list) - for pre-provisioning access
    - Role assignment (assign roles to users or invitations)
    - Team management (list, add/remove members)
    """

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._token: Optional[str] = None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        if self._token is None:
            self._token = self._exchange_api_key()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _exchange_api_key(self) -> str:
        """Exchange API key for a short-lived access token."""
        response = requests.post(
            f"{self.api_url}/auth/login",
            data={"password": self.api_key},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()["access_token"]

    # =========================================================================
    # User Management
    # =========================================================================

    def list_users(self, email: Optional[str] = None) -> list[dict]:
        """List users in ZenML Pro.

        Args:
            email: Optional email filter.

        Returns:
            List of user objects.
        """
        params = {}
        if email:
            params["email"] = email
        response = requests.get(
            f"{self.api_url}/users",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Find a user by email address."""
        users = self.list_users(email=email)
        for user in users:
            if user.get("email") == email:
                return user
        return None

    def update_user(self, user_id: str, **kwargs) -> dict:
        """Update a user's attributes.

        Args:
            user_id: The user ID.
            **kwargs: Fields to update (e.g., is_active, username).

        Returns:
            Updated user object.
        """
        response = requests.patch(
            f"{self.api_url}/users/{user_id}",
            headers=self._get_headers(),
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()

    def deactivate_user(self, user_id: str) -> dict:
        """Deactivate a user account."""
        return self.update_user(user_id, is_active=False)

    # =========================================================================
    # Organization Management
    # =========================================================================

    def list_organizations(self) -> list[dict]:
        """List all organizations the authenticated user has access to."""
        response = requests.get(
            f"{self.api_url}/organizations",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def list_organization_roles(
        self,
        org_id: str,
        level: Optional[str] = None,
        name: Optional[str] = None,
    ) -> list[dict]:
        """List roles defined in an organization.

        Args:
            org_id: Organization ID.
            level: Filter by role level (organization, workspace, project).
            name: Filter by role name.

        Returns:
            List of role objects.
        """
        params = {}
        if level:
            params["level"] = level
        if name:
            params["name"] = name
        response = requests.get(
            f"{self.api_url}/organizations/{org_id}/roles",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_organization_role_by_name(
        self, org_id: str, role_name: str, level: str = "organization"
    ) -> Optional[dict]:
        """Get an organization role by name.

        Args:
            org_id: Organization ID.
            role_name: Role name to find.
            level: Role level (organization, workspace, project).

        Returns:
            Role object or None if not found.
        """
        roles = self.list_organization_roles(org_id, level=level, name=role_name)
        for role in roles:
            if role.get("name") == role_name:
                return role
        return None

    def list_organization_members(self, org_id: str) -> list[dict]:
        """List members of an organization.

        Returns users, service accounts, teams, and pending invitations.
        """
        response = requests.get(
            f"{self.api_url}/organizations/{org_id}/members",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def remove_user_from_organization(self, org_id: str, user_id: str) -> None:
        """Remove a user from an organization.

        This removes all of the user's organization-level role assignments.
        """
        response = requests.delete(
            f"{self.api_url}/organizations/{org_id}/members",
            headers=self._get_headers(),
            params={"user_id": user_id},
        )
        response.raise_for_status()

    # =========================================================================
    # Invitation Management
    # =========================================================================

    def create_invitation(
        self, org_id: str, email: str, role_id: str
    ) -> dict:
        """Create an invitation to join an organization.

        Invitations act as placeholders for users who haven't logged in yet.
        You can assign additional roles and team memberships to invitations.
        When the user logs in via SSO and accepts the invitation, all
        permissions are transferred to their user account.

        Args:
            org_id: Organization ID.
            email: Email address to invite (should match IdP email).
            role_id: Organization-level role ID to assign initially.

        Returns:
            Invitation object.
        """
        response = requests.post(
            f"{self.api_url}/organizations/{org_id}/invitations",
            headers=self._get_headers(),
            json={"email": email, "role_id": role_id},
        )
        response.raise_for_status()
        return response.json()

    def list_invitations(
        self, org_id: str, email: Optional[str] = None, only_pending: bool = True
    ) -> list[dict]:
        """List invitations for an organization.

        Args:
            org_id: Organization ID.
            email: Filter by email address.
            only_pending: If True, only return pending invitations.

        Returns:
            List of invitation objects.
        """
        params = {"only_pending": only_pending}
        if email:
            params["email"] = email
        response = requests.get(
            f"{self.api_url}/organizations/{org_id}/invitations",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_pending_invitation_by_email(
        self, org_id: str, email: str
    ) -> Optional[dict]:
        """Get a pending invitation by email."""
        invitations = self.list_invitations(org_id, email=email, only_pending=True)
        for inv in invitations:
            if inv.get("email") == email:
                return inv
        return None

    def delete_invitation(self, org_id: str, invitation_id: str) -> None:
        """Delete an invitation."""
        response = requests.delete(
            f"{self.api_url}/organizations/{org_id}/invitations/{invitation_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()

    # =========================================================================
    # Role Assignment
    # =========================================================================

    def assign_role(
        self,
        role_id: str,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
        team_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict:
        """Assign a role to a user, invitation, or team.

        This is the primary mechanism for granting access in ZenML Pro.
        Organization membership is established by assigning organization-level
        roles. Workspace and project access is granted by assigning roles at
        those respective levels.

        Args:
            role_id: Role ID to assign.
            user_id: User ID (for existing users).
            invitation_id: Invitation ID (for users who haven't logged in).
            team_id: Team ID (to assign role to entire team).
            workspace_id: Workspace scope (for workspace/project roles).
            project_id: Project scope (for project roles).

        Returns:
            Role assignment object.
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        if invitation_id:
            params["invitation_id"] = invitation_id
        if team_id:
            params["team_id"] = team_id
        if workspace_id:
            params["workspace_id"] = workspace_id
        if project_id:
            params["project_id"] = project_id

        response = requests.post(
            f"{self.api_url}/roles/{role_id}/assignments",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def revoke_role(
        self,
        role_id: str,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
        team_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """Revoke a role from a user, invitation, or team."""
        params = {}
        if user_id:
            params["user_id"] = user_id
        if invitation_id:
            params["invitation_id"] = invitation_id
        if team_id:
            params["team_id"] = team_id
        if workspace_id:
            params["workspace_id"] = workspace_id
        if project_id:
            params["project_id"] = project_id

        response = requests.delete(
            f"{self.api_url}/roles/{role_id}/assignments",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()

    # =========================================================================
    # Team Management
    # =========================================================================

    def list_teams(self, org_id: str) -> list[dict]:
        """List all teams in an organization."""
        response = requests.get(
            f"{self.api_url}/organizations/{org_id}/teams",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_team_by_name(self, org_id: str, team_name: str) -> Optional[dict]:
        """Get a team by name."""
        teams = self.list_teams(org_id)
        for team in teams:
            if team.get("name") == team_name:
                return team
        return None

    def add_to_team(
        self,
        team_id: str,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
    ) -> None:
        """Add a user or invitation to a team.

        Teams use a separate endpoint from roles. You can add either a user
        (by user_id) or an invitation (by invitation_id) to a team.

        Args:
            team_id: Team ID.
            user_id: User ID (for existing users).
            invitation_id: Invitation ID (for users who haven't logged in).
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        if invitation_id:
            params["invitation_id"] = invitation_id

        response = requests.post(
            f"{self.api_url}/teams/{team_id}/members",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()

    def remove_from_team(
        self,
        team_id: str,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
    ) -> None:
        """Remove a user or invitation from a team."""
        params = {}
        if user_id:
            params["user_id"] = user_id
        if invitation_id:
            params["invitation_id"] = invitation_id

        response = requests.delete(
            f"{self.api_url}/teams/{team_id}/members",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()


class UserSynchronizer:
    """Synchronizes users between an IdP and ZenML Pro.

    This synchronizer handles two scenarios:
    1. Users who have already logged in via SSO (have a ZenML user account)
    2. Users who haven't logged in yet (use invitations as placeholders)

    For users who haven't logged in, the synchronizer creates invitations and
    assigns roles/teams to those invitations. When users log in via SSO and
    accept the invitation, all permissions are automatically transferred.
    """

    # Predefined organization role names (see roles.md for full list)
    ORG_ROLE_ADMIN = "Organization Admin"
    ORG_ROLE_MANAGER = "Organization Manager"
    ORG_ROLE_VIEWER = "Organization Viewer"
    ORG_ROLE_BILLING = "Billing Admin"
    ORG_ROLE_MEMBER = "Organization Member"

    # Predefined workspace role names
    WS_ROLE_ADMIN = "Workspace Admin"
    WS_ROLE_DEVELOPER = "Workspace Developer"
    WS_ROLE_CONTRIBUTOR = "Workspace Contributor"
    WS_ROLE_VIEWER = "Workspace Viewer"
    WS_ROLE_STACK_ADMIN = "Stack Admin"

    # ==========================================================================
    # Mapping Configuration - CUSTOMIZE THIS FOR YOUR ORGANIZATION
    # ==========================================================================
    # Format: IdP group name -> (ZenML org name, ZenML org role name)
    ORG_GROUP_MAPPING = {
        "zenml-production-admins": ("Production", ORG_ROLE_ADMIN),
        "zenml-production-users": ("Production", ORG_ROLE_MEMBER),
        "zenml-development-admins": ("Development", ORG_ROLE_ADMIN),
        "zenml-development-users": ("Development", ORG_ROLE_MEMBER),
    }

    # Format: IdP group name -> (ZenML org name, ZenML team name)
    TEAM_GROUP_MAPPING = {
        "zenml-ds-team": ("Production", "Data Science"),
        "zenml-mlops-team": ("Production", "MLOps"),
        "zenml-dev-team": ("Development", "Engineering"),
    }

    def __init__(self, idp_client: IdPClient, zenml_client: ZenMLProClient):
        self.idp = idp_client
        self.zenml = zenml_client
        self._org_cache: dict[str, dict] = {}
        self._role_cache: dict[str, dict[str, dict]] = {}
        self._team_cache: dict[str, dict[str, dict]] = {}

    def _get_org_by_name(self, name: str) -> Optional[dict]:
        """Get organization by name with caching."""
        if not self._org_cache:
            for org in self.zenml.list_organizations():
                self._org_cache[org["name"]] = org
        return self._org_cache.get(name)

    def _get_role_by_name(
        self, org_id: str, role_name: str, level: str = "organization"
    ) -> Optional[dict]:
        """Get role by name with caching."""
        cache_key = f"{org_id}:{level}"
        if cache_key not in self._role_cache:
            self._role_cache[cache_key] = {}
            roles = self.zenml.list_organization_roles(org_id, level=level)
            for role in roles:
                self._role_cache[cache_key][role["name"]] = role
        return self._role_cache[cache_key].get(role_name)

    def _get_team_by_name(self, org_id: str, team_name: str) -> Optional[dict]:
        """Get team by name with caching."""
        if org_id not in self._team_cache:
            self._team_cache[org_id] = {}
            for team in self.zenml.list_teams(org_id):
                self._team_cache[org_id][team["name"]] = team
        return self._team_cache[org_id].get(team_name)

    def sync_user(self, idp_user: IdPUser) -> None:
        """Synchronize a single user from IdP to ZenML Pro.

        If the user has logged in via SSO, they have a ZenML user account and
        we sync directly to that account. If they haven't logged in yet, we
        create/update an invitation that serves as a placeholder.
        """
        logger.info(f"Synchronizing user: {idp_user.email}")

        zenml_user = self.zenml.get_user_by_email(idp_user.email)

        if zenml_user is not None:
            # User has logged in via SSO - sync to their user account
            if not idp_user.is_active:
                logger.info(f"Deactivating user: {idp_user.email}")
                self.zenml.deactivate_user(zenml_user["id"])
                return

            self._sync_organization_memberships(
                idp_user, user_id=zenml_user["id"]
            )
            self._sync_team_memberships(idp_user, user_id=zenml_user["id"])
        else:
            # User hasn't logged in yet - use invitations as placeholders
            if not idp_user.is_active:
                logger.info(
                    f"Skipping inactive IdP user without ZenML account: "
                    f"{idp_user.email}"
                )
                return

            logger.info(
                f"User not in ZenML Pro yet, setting up invitation: "
                f"{idp_user.email}"
            )
            self._sync_via_invitations(idp_user)

    def _sync_via_invitations(self, idp_user: IdPUser) -> None:
        """Set up invitations for a user who hasn't logged in yet.

        Creates invitations in each organization the user should belong to,
        then assigns additional roles and team memberships to those invitations.
        """
        # Group the user's groups by organization
        org_groups: dict[str, list[str]] = {}
        for group in idp_user.groups:
            if group in self.ORG_GROUP_MAPPING:
                org_name, _ = self.ORG_GROUP_MAPPING[group]
                org_groups.setdefault(org_name, []).append(group)
            elif group in self.TEAM_GROUP_MAPPING:
                org_name, _ = self.TEAM_GROUP_MAPPING[group]
                org_groups.setdefault(org_name, []).append(group)

        for org_name, groups in org_groups.items():
            org = self._get_org_by_name(org_name)
            if org is None:
                logger.warning(f"Organization not found: {org_name}")
                continue

            # Check if invitation already exists
            invitation = self.zenml.get_pending_invitation_by_email(
                org["id"], idp_user.email
            )

            if invitation is None:
                # Find the first org role to use for the invitation
                initial_role_name = self.ORG_ROLE_MEMBER
                for group in groups:
                    if group in self.ORG_GROUP_MAPPING:
                        _, role_name = self.ORG_GROUP_MAPPING[group]
                        initial_role_name = role_name
                        break

                initial_role = self._get_role_by_name(
                    org["id"], initial_role_name, level="organization"
                )
                if initial_role is None:
                    logger.warning(
                        f"Role not found: {initial_role_name} in {org_name}"
                    )
                    continue

                try:
                    invitation = self.zenml.create_invitation(
                        org["id"], idp_user.email, initial_role["id"]
                    )
                    logger.info(
                        f"Created invitation for {idp_user.email} in {org_name}"
                    )
                except requests.HTTPError as e:
                    logger.error(
                        f"Failed to create invitation: {e.response.text}"
                    )
                    continue

            # Assign additional org roles to the invitation
            self._sync_organization_memberships(
                idp_user,
                invitation_id=invitation["id"],
                org_filter=org_name,
            )

            # Assign team memberships to the invitation
            self._sync_team_memberships(
                idp_user,
                invitation_id=invitation["id"],
                org_filter=org_name,
            )

    def _sync_organization_memberships(
        self,
        idp_user: IdPUser,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
        org_filter: Optional[str] = None,
    ) -> None:
        """Sync organization memberships by assigning organization roles."""
        for group in idp_user.groups:
            if group not in self.ORG_GROUP_MAPPING:
                continue

            org_name, role_name = self.ORG_GROUP_MAPPING[group]

            if org_filter and org_name != org_filter:
                continue

            org = self._get_org_by_name(org_name)
            if org is None:
                logger.warning(f"Organization not found: {org_name}")
                continue

            role = self._get_role_by_name(
                org["id"], role_name, level="organization"
            )
            if role is None:
                logger.warning(f"Role not found: {role_name} in {org_name}")
                continue

            try:
                self.zenml.assign_role(
                    role["id"],
                    user_id=user_id,
                    invitation_id=invitation_id,
                )
                target = "user" if user_id else "invitation"
                logger.info(
                    f"Assigned {role_name} to {target} in {org_name}"
                )
            except requests.HTTPError as e:
                if e.response.status_code == 409:
                    logger.debug(f"Role already assigned: {role_name}")
                else:
                    logger.error(f"Failed to assign role: {e.response.text}")

    def _sync_team_memberships(
        self,
        idp_user: IdPUser,
        user_id: Optional[str] = None,
        invitation_id: Optional[str] = None,
        org_filter: Optional[str] = None,
    ) -> None:
        """Sync team memberships."""
        for group in idp_user.groups:
            if group not in self.TEAM_GROUP_MAPPING:
                continue

            org_name, team_name = self.TEAM_GROUP_MAPPING[group]

            if org_filter and org_name != org_filter:
                continue

            org = self._get_org_by_name(org_name)
            if org is None:
                logger.warning(f"Organization not found: {org_name}")
                continue

            team = self._get_team_by_name(org["id"], team_name)
            if team is None:
                logger.warning(f"Team not found: {team_name} in {org_name}")
                continue

            try:
                self.zenml.add_to_team(
                    team["id"],
                    user_id=user_id,
                    invitation_id=invitation_id,
                )
                target = "user" if user_id else "invitation"
                logger.info(f"Added {target} to team {team_name}")
            except requests.HTTPError as e:
                if e.response.status_code == 409:
                    logger.debug(f"Already in team: {team_name}")
                else:
                    logger.error(f"Failed to add to team: {e.response.text}")

    def sync_all(self) -> None:
        """Synchronize all users from IdP to ZenML Pro."""
        logger.info("Starting user synchronization")

        idp_users = self.idp.list_users()
        logger.info(f"Found {len(idp_users)} users in IdP")

        for idp_user in idp_users:
            try:
                self.sync_user(idp_user)
            except Exception:
                logger.exception(f"Failed to sync user: {idp_user.email}")

        logger.info("User synchronization complete")


def main():
    """Main entry point for the synchronization script."""
    zenml_api_url = os.environ.get("ZENML_PRO_API_URL")
    zenml_api_key = os.environ.get("ZENML_PRO_API_KEY")
    idp_url = os.environ.get("IDP_URL")
    idp_token = os.environ.get("IDP_TOKEN")

    if not all([zenml_api_url, zenml_api_key]):
        raise ValueError(
            "ZENML_PRO_API_URL and ZENML_PRO_API_KEY must be set"
        )

    if not all([idp_url, idp_token]):
        raise ValueError("IDP_URL and IDP_TOKEN must be set")

    idp_client = IdPClient(idp_url, idp_token)
    zenml_client = ZenMLProClient(zenml_api_url, zenml_api_key)

    synchronizer = UserSynchronizer(idp_client, zenml_client)
    synchronizer.sync_all()


if __name__ == "__main__":
    main()
