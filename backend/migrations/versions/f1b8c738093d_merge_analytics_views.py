"""merge analytics views

Revision ID: f1b8c738093d
Revises: 0004_create_analytics_users_v, 0004_fix_analytics_users_v
Create Date: 2025-12-19 21:14:44.760941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1b8c738093d'
down_revision: Union[str, Sequence[str], None] = ('0004_create_analytics_users_v', '0004_fix_analytics_users_v')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
