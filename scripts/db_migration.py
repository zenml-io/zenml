import argparse
import asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from zenmlcloud.database import create_db_and_tables, initialize_engine
from zenmlcloud.enums import SubscriptionStatus, TenantStatus
from zenmlcloud.public.organization.crud import (
    create_organization,
)
from zenmlcloud.public.organization.models import InternalOrganizationCreate
from zenmlcloud.public.tenant.crud import create_tenant, list_tenants
from zenmlcloud.public.tenant.models import TenantCreate
from zenmlcloud.public.user.crud import (
    create_user,
    get_user,
)
from zenmlcloud.public.user.models import UserCreate

USER_NAME = "Test User"
USER_EMAIL = "test@zenml.io"
USER_OAUTH_PROVIDER = "oauth_provider"
USER_OAUTH_ID = "oauth_id"
ORGANIZATION_NAME = "organization_name"
TENANT_NAME = "tenant_name"
SUBSCRIPTION_ID = "subscription_id"
CUSTOMER_ID = "customer_id"


async def create_data():
    engine = initialize_engine()

    async with AsyncSession(engine, expire_on_commit=False) as db:
        user_create = UserCreate(
            name=USER_NAME,
            email=USER_EMAIL,
            oauth_provider=USER_OAUTH_PROVIDER,
            oauth_id=USER_OAUTH_ID,
            is_verified=True,
        )
        user = await create_user(db=db, user=user_create)

        organization_create = InternalOrganizationCreate(
            name=ORGANIZATION_NAME,
            owner_id=user.id,
            stripe_customer_id=CUSTOMER_ID,
            stripe_subscription_id=SUBSCRIPTION_ID,
            subscription_status=SubscriptionStatus.TRIALING,
        )
        organization = await create_organization(
            db=db, organization=organization_create
        )

        tenant_create = TenantCreate(
            status=TenantStatus.AVAILABLE,
            organization_id=organization.id,
            name=TENANT_NAME,
        )
        await create_tenant(db=db, tenant_create=tenant_create)


async def verify_data():
    engine = initialize_engine()

    async with AsyncSession(engine, expire_on_commit=False) as db:
        user = await get_user(
            db=db, oauth_provider=USER_OAUTH_PROVIDER, oauth_id=USER_OAUTH_ID
        )

        assert user.name == USER_NAME
        assert user.email == USER_EMAIL

        assert len(user.owned_organizations) == 1
        organization = user.owned_organizations[0]
        assert organization.stripe_customer_id == CUSTOMER_ID
        assert organization.stripe_subscription_id == SUBSCRIPTION_ID
        assert organization.subscription_status == SubscriptionStatus.TRIALING

        tenant = await list_tenants(db=db, organization_id=organization.id)
        assert tenant[0].name == TENANT_NAME
        assert tenant[0].status == TenantStatus.AVAILABLE


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.set_defaults(create=False, verify=False)

    args, _ = parser.parse_known_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_db_and_tables())

    if args.create:
        loop.run_until_complete(create_data())

    if args.verify:
        loop.run_until_complete(verify_data())
