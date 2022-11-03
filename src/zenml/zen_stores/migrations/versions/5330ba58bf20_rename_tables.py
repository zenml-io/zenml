"""Rename tables [5330ba58bf20].

Revision ID: 5330ba58bf20
Revises: d02b3d3464cf
Create Date: 2022-11-03 16:33:15.220179

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "5330ba58bf20"
down_revision = "d02b3d3464cf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.rename_table("roleschema", "role")
    op.rename_table("stepinputartifactschema", "step_run_artifact")
    op.rename_table("userroleassignmentschema", "user_role_assignment")
    op.rename_table("steprunorderschema", "step_run_parents")
    op.rename_table("teamschema", "team")
    op.rename_table("artifactschema", "artifact")
    op.rename_table("pipelinerunschema", "pipeline_run")
    op.rename_table("steprunschema", "step_run")
    op.rename_table("teamassignmentschema", "team_assignment")
    op.rename_table("projectschema", "project")
    op.rename_table("flavorschema", "flavor")
    op.rename_table("userschema", "user")
    op.rename_table("stackcomponentschema", "stack_component")
    op.rename_table("pipelineschema", "pipeline")
    op.rename_table("stackcompositionschema", "stack_composition")
    op.rename_table("teamroleassignmentschema", "team_role_assignment")
    op.rename_table("stackschema", "stack")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.rename_table("step_run_artifact", "stepinputartifactschema")
    op.rename_table("step_run_parents", "steprunorderschema")
    op.rename_table("artifact", "artifactschema")
    op.rename_table("step_run", "steprunschema")
    op.rename_table("stack_composition", "stackcompositionschema")
    op.rename_table("pipeline_run", "pipelinerunschema")
    op.rename_table("user_role_assignment", "userroleassignmentschema")
    op.rename_table("team_role_assignment", "teamroleassignmentschema")
    op.rename_table("team_assignment", "teamassignmentschema")
    op.rename_table("stack_component", "stackcomponentschema")
    op.rename_table("stack", "stackschema")
    op.rename_table("pipeline", "pipelineschema")
    op.rename_table("flavor", "flavorschema")
    op.rename_table("user", "userschema")
    op.rename_table("team", "teamschema")
    op.rename_table("role", "roleschema")
    op.rename_table("project", "projectschema")
