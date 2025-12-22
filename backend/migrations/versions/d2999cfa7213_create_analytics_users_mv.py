from alembic import op

revision = "0003_analytics_users_mv"
down_revision = "0002_create_triggers"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE MATERIALIZED VIEW analytics_users_mv AS
        SELECT
            u.id                AS user_id,
            u.telegram_id       AS telegram_id,
            u.username          AS username,
            u.language          AS language,

            u.plan              AS plan,
            u.plan_expires_at   AS plan_expires_at,

            CASE
                WHEN u.plan_expires_at IS NULL THEN true
                ELSE u.plan_expires_at > NOW()
            END                 AS is_plan_active,

            u.trigger_count     AS trigger_count,

            COUNT(t.id)         AS real_trigger_count,

            u.worker_active     AS worker_active,
            u.is_registered     AS is_registered,

            u.registered_at     AS registered_at,
            u.last_seen_at      AS last_seen_at,
            u.created_at        AS created_at

        FROM users u
        LEFT JOIN triggers t ON t.user_id = u.id
        GROUP BY u.id;
    """)

    # CONCURRENT refresh uchun unique index SHART
    op.execute("""
        CREATE UNIQUE INDEX analytics_users_mv_user_id_idx
        ON analytics_users_mv (user_id);
    """)


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics_users_mv;")