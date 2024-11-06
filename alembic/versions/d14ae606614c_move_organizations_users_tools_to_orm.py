"""Move organizations users tools to orm

Revision ID: d14ae606614c
Revises: 9a505cc7eca9
Create Date: 2024-11-05 15:03:12.350096

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import letta
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d14ae606614c"
down_revision: Union[str, None] = "9a505cc7eca9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def deprecated_tool():
    return "this is a deprecated tool, please remove it from your tools list"


def upgrade() -> None:
    # Delete all tools
    op.execute("DELETE FROM tools")

    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("agents", sa.Column("tool_rules", letta.metadata.ToolRulesColumn(), nullable=True))
    op.alter_column("block", "name", new_column_name="template_name", nullable=True)
    op.add_column("organizations", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
    op.add_column("organizations", sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    op.add_column("organizations", sa.Column("_created_by_id", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("_last_updated_by_id", sa.String(), nullable=True))
    op.add_column("tools", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
    op.add_column("tools", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
    op.add_column("tools", sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    op.add_column("tools", sa.Column("_created_by_id", sa.String(), nullable=True))
    op.add_column("tools", sa.Column("_last_updated_by_id", sa.String(), nullable=True))
    op.add_column("tools", sa.Column("organization_id", sa.String(), nullable=False))
    op.alter_column("tools", "tags", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=False)
    op.alter_column("tools", "source_type", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column("tools", "json_schema", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=False)
    op.create_unique_constraint("uix_name_organization", "tools", ["name", "organization_id"])
    op.create_foreign_key(None, "tools", "organizations", ["organization_id"], ["id"])
    op.drop_column("tools", "user_id")
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
    op.add_column("users", sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    op.add_column("users", sa.Column("_created_by_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("_last_updated_by_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("organization_id", sa.String(), nullable=True))
    # loop through all rows in the user table and set the _organization_id column from organization_id
    op.execute('UPDATE "users" SET organization_id = org_id')
    # set the _organization_id column to not nullable
    op.alter_column("users", "organization_id", existing_type=sa.String(), nullable=False)
    op.create_foreign_key(None, "users", "organizations", ["organization_id"], ["id"])
    op.drop_column("users", "org_id")
    op.drop_column("users", "policies_accepted")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("policies_accepted", sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column("users", sa.Column("org_id", sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, "users", type_="foreignkey")
    op.drop_column("users", "organization_id")
    op.drop_column("users", "_last_updated_by_id")
    op.drop_column("users", "_created_by_id")
    op.drop_column("users", "is_deleted")
    op.drop_column("users", "updated_at")
    op.add_column("tools", sa.Column("user_id", sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, "tools", type_="foreignkey")
    op.drop_constraint("uix_name_organization", "tools", type_="unique")
    op.alter_column("tools", "json_schema", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=True)
    op.alter_column("tools", "source_type", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("tools", "tags", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=True)
    op.drop_column("tools", "organization_id")
    op.drop_column("tools", "_last_updated_by_id")
    op.drop_column("tools", "_created_by_id")
    op.drop_column("tools", "is_deleted")
    op.drop_column("tools", "updated_at")
    op.drop_column("tools", "created_at")
    op.drop_column("organizations", "_last_updated_by_id")
    op.drop_column("organizations", "_created_by_id")
    op.drop_column("organizations", "is_deleted")
    op.drop_column("organizations", "updated_at")
    op.add_column("block", sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column("block", "template_name")
    op.drop_column("agents", "tool_rules")
    # ### end Alembic commands ###
