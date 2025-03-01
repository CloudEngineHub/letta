"""add args schema to tools

Revision ID: 54f2311edb62
Revises: b183663c6769
Create Date: 2025-02-27 16:45:50.835081

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54f2311edb62"
down_revision: Union[str, None] = "b183663c6769"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("tools", sa.Column("args_json_schema", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("tools", "args_json_schema")
    # ### end Alembic commands ###
