from alembic import op

revision = "0004_fix_analytics_users_v"
down_revision = "0003_analytics_users_mv"
branch_labels = None
depends_on = None


def upgrade():
    # ESKI VIEW’NI BUTUNLAY O‘CHIRAMIZ
    op.execute("DROP VIEW IF EXISTS analytics_users_v;")

    # YANGI TOZA VIEW
    op.execute("""
        CREATE VIEW analytics_users_v AS
        SELECT
            u.id              AS user_id,
            u.telegram_id     AS telegram_id,
            u.language        AS language,

            u.plan            AS plan,
            u.plan_expires_at AS plan_expires_at,

            CASE
                WHEN u.plan_expires_at IS NULL THEN true
                ELSE u.plan_expires_at > NOW()
            END               AS is_plan_active,

            COUNT(t.id)       AS real_trigger_count,

            u.registered_at   AS registered_at,
            u.created_at      AS created_at

        FROM users u
        LEFT JOIN triggers t ON t.user_id = u.id
        GROUP BY u.id;
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS analytics_users_v;")