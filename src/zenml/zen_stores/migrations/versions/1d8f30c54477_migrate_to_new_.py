"""migrate to new ModelVersionDataLazyLoader structures [1d8f30c54477].

Revision ID: 1d8f30c54477
Revises: 0.67.0
Create Date: 2024-10-08 15:55:34.727543

"""

import json

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "1d8f30c54477"
down_revision = "0.67.0"
branch_labels = None
depends_on = None


update_query_pd = sa.text(
    "UPDATE pipeline_deployment SET step_configurations = :data WHERE id = :id_"
)

update_query_sr = sa.text(
    "UPDATE step_run SET step_configuration = :data WHERE id = :id_"
)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    bind = op.get_bind()
    session = sqlmodel.Session(bind=bind)
    # update pipeline_deployment
    rows_pd = session.execute(
        sa.text(
            """
             SELECT id, step_configurations 
             FROM pipeline_deployment 
             WHERE step_configurations IS NOT NULL
             """
        )
    )
    for id_, data in rows_pd:
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError:
            continue
        has_changes = False
        for k in data_dict:
            if config := data_dict[k].get("config", {}):
                if model_artifacts_or_metadata := config.get(
                    "model_artifacts_or_metadata", {}
                ):
                    for (
                        inp_name,
                        inp_config,
                    ) in model_artifacts_or_metadata.items():
                        if model := inp_config.get("model", {}):
                            del data_dict[k]["config"][
                                "model_artifacts_or_metadata"
                            ][inp_name]["model"]
                            data_dict[k]["config"][
                                "model_artifacts_or_metadata"
                            ][inp_name]["model_name"] = model["name"]
                            data_dict[k]["config"][
                                "model_artifacts_or_metadata"
                            ][inp_name]["model_version"] = str(
                                model["version"]
                            )
                            has_changes = True
        if has_changes:
            data = json.dumps(data_dict)
            session.execute(update_query_pd, params=(dict(data=data, id_=id_)))

    # update step_run
    rows_sr = session.execute(
        sa.text(
            """
             SELECT id, step_configuration 
             FROM step_run 
             WHERE step_configuration IS NOT NULL
             """
        )
    )
    for id_, data in rows_sr:
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError:
            continue
        has_changes = False
        if config := data_dict.get("config", {}):
            if model_artifacts_or_metadata := config.get(
                "model_artifacts_or_metadata", {}
            ):
                for (
                    inp_name,
                    inp_config,
                ) in model_artifacts_or_metadata.items():
                    if model := inp_config.get("model", {}):
                        del data_dict["config"]["model_artifacts_or_metadata"][
                            inp_name
                        ]["model"]
                        data_dict["config"]["model_artifacts_or_metadata"][
                            inp_name
                        ]["model_name"] = model["name"]
                        data_dict["config"]["model_artifacts_or_metadata"][
                            inp_name
                        ]["model_version"] = str(model["version"])
                        has_changes = True
        if has_changes:
            data = json.dumps(data_dict)
            session.execute(update_query_sr, params=(dict(data=data, id_=id_)))
    session.commit()


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not supported for this migration.
    """
    raise NotImplementedError("Downgrade is not supported for this migration.")
