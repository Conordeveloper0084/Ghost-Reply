"""add worker_id to users

Revision ID: 5e7ead044c70
Revises: f1b8c738093d
Create Date: 2025-12-21 13:00:50.440412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e7ead044c70'
down_revision: Union[str, Sequence[str], None] = 'f1b8c738093d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column(
        "users",
        sa.Column("worker_id", sa.String(length=64), nullable=True)
    )


def downgrade():
    op.drop_column("users", "worker_id")