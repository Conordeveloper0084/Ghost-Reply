from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # USERS
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_id", sa.BigInteger, unique=True, nullable=False, index=True),

        sa.Column("name", sa.String),
        sa.Column("username", sa.String),
        sa.Column("phone", sa.String),

        sa.Column("language", sa.String, server_default="uz", nullable=False),

        sa.Column("registered_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),

        sa.Column("worker_active", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime),

        sa.Column(
            "plan",
            sa.Enum("free", "pro", "premium", name="plan_enum"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("plan_expires_at", sa.DateTime),

        sa.Column("is_registered", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("trigger_count", sa.Integer, server_default="0", nullable=False),
    )

    # TELEGRAM SESSIONS
    op.create_table(
        "telegram_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("telegram_id", sa.BigInteger, unique=True, nullable=False, index=True),
        sa.Column("session_string", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("telegram_sessions")
    op.drop_table("users")
    op.execute("DROP TYPE plan_enum")