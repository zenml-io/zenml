"""Migrate onboarding state [b4fca5241eea].

Revision ID: b4fca5241eea
Revises: 0.58.2
Create Date: 2024-06-20 15:01:22.414801

"""

import json
from typing import Dict, List

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4fca5241eea"
down_revision = "0.58.2"
branch_labels = None
depends_on = None


ONBOARDING_KEY_MAPPING = {
    "connect_zenml": ["device_verified"],
    "run_first_pipeline": ["pipeline_run", "starter_setup_completed"],
    "create_service_connector": ["service_connector_created"],
    "create_remote_artifact_store": ["remote_artifact_store_created"],
    "create_remote_stack": ["stack_with_remote_artifact_store_created"],
    "run_remote_pipeline": [
        "pipeline_run_with_remote_artifact_store",
        "production_setup_completed",
    ],
}


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(only=("server_settings",), bind=connection)

    server_settings_table = sa.Table("server_settings", meta)

    existing_onboarding_state = connection.execute(
        sa.select(server_settings_table.c.onboarding_state)
    ).scalar_one_or_none()

    new_state = []

    if existing_onboarding_state:
        # Case 1: There was already an existing onboarding state in the DB
        # -> Migrate to the new server keys
        state = json.loads(existing_onboarding_state)

        if isinstance(state, Dict):
            for key in state.keys():
                if key in ONBOARDING_KEY_MAPPING:
                    new_state.extend(ONBOARDING_KEY_MAPPING[key])
        elif isinstance(state, List):
            # Somehow the state is already converted, probably shouldn't happen
            return
    else:
        # Case 2: There is no onboarding state in the DB. This is the case when
        # updating from an old version or cloud tenants which previously used
        # an external tool to store the onboarding progress
        # -> Query the DB to figure out which steps are already completed
        meta = sa.MetaData()
        meta.reflect(
            only=(
                "pipeline_run",
                "stack_component",
                "stack",
                "stack_composition",
                "service_connector",
                "pipeline_deployment",
            ),
            bind=connection,
        )

        pipeline_run_table = sa.Table("pipeline_run", meta)
        service_connector_table = sa.Table("service_connector", meta)
        stack_component_table = sa.Table("stack_component", meta)
        stack_table = sa.Table("stack", meta)
        stack_composition_table = sa.Table("stack_composition", meta)
        pipeline_deployment_table = sa.Table("pipeline_deployment", meta)

        pipeline_run_count = connection.execute(
            sa.select(sa.func.count(pipeline_run_table.c.id))
        ).scalar()
        if pipeline_run_count > 0:
            new_state.extend(ONBOARDING_KEY_MAPPING["run_first_pipeline"])

        service_connector_count = connection.execute(
            sa.select(sa.func.count(service_connector_table.c.id))
        ).scalar()
        if service_connector_count > 0:
            new_state.extend(
                ONBOARDING_KEY_MAPPING["create_service_connector"]
            )

        remote_artifact_store_count = connection.execute(
            sa.select(sa.func.count(stack_component_table.c.id))
            .where(stack_component_table.c.flavor != "local")
            .where(stack_component_table.c.type == "artifact_store")
        ).scalar()
        if remote_artifact_store_count > 0:
            new_state.extend(
                ONBOARDING_KEY_MAPPING["create_remote_artifact_store"]
            )

        remote_stack_count = connection.execute(
            sa.select(sa.func.count(stack_table.c.id))
            .where(stack_composition_table.c.stack_id == stack_table.c.id)
            .where(
                stack_composition_table.c.component_id
                == stack_component_table.c.id
            )
            .where(stack_component_table.c.flavor != "local")
            .where(stack_component_table.c.type == "artifact_store")
        ).scalar()
        if remote_stack_count > 0:
            new_state.extend(ONBOARDING_KEY_MAPPING["create_remote_stack"])

        remote_pipeline_run_count = connection.execute(
            sa.select(sa.func.count(pipeline_run_table.c.id))
            .where(
                pipeline_run_table.c.deployment_id
                == pipeline_deployment_table.c.id
            )
            .where(pipeline_deployment_table.c.stack_id == stack_table.c.id)
            .where(stack_composition_table.c.stack_id == stack_table.c.id)
            .where(
                stack_composition_table.c.component_id
                == stack_component_table.c.id
            )
            .where(stack_component_table.c.flavor != "local")
            .where(stack_component_table.c.type == "artifact_store")
        ).scalar()
        if remote_pipeline_run_count > 0:
            new_state.extend(ONBOARDING_KEY_MAPPING["run_remote_pipeline"])

        if new_state:
            # If any of the items are finished, we also complete the initial
            # onboarding step which is not explicitly tracked in the database
            new_state.append("device_verified")

    connection.execute(
        sa.update(server_settings_table).values(
            onboarding_state=json.dumps(new_state)
        )
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
