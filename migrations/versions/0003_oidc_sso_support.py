"""add oidc account binding fields

Revision ID: 0003_oidc_sso_support
Revises: 0002_session_refresh_tokens
Create Date: 2026-05-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_oidc_sso_support"
down_revision = "0002_session_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_accounts", sa.Column("auth_provider", sa.String(length=32), nullable=True))
    op.add_column("user_accounts", sa.Column("external_subject", sa.String(length=255), nullable=True))
    op.add_column("user_accounts", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    user_accounts = sa.table(
        "user_accounts",
        sa.column("auth_provider", sa.String(length=32)),
    )
    bind.execute(
        user_accounts.update()
        .where(user_accounts.c.auth_provider.is_(None))
        .values(auth_provider="local")
    )

    op.alter_column("user_accounts", "auth_provider", existing_type=sa.String(length=32), nullable=False)
    op.create_index("ix_user_accounts_auth_provider", "user_accounts", ["auth_provider"], unique=False)
    op.create_index("ix_user_accounts_external_subject", "user_accounts", ["external_subject"], unique=False)
    op.create_index("ix_user_accounts_last_login_at", "user_accounts", ["last_login_at"], unique=False)
    op.create_unique_constraint(
        "uq_user_accounts_org_provider_subject",
        "user_accounts",
        ["organization_id", "auth_provider", "external_subject"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_accounts_org_provider_subject", "user_accounts", type_="unique")
    op.drop_index("ix_user_accounts_last_login_at", table_name="user_accounts")
    op.drop_index("ix_user_accounts_external_subject", table_name="user_accounts")
    op.drop_index("ix_user_accounts_auth_provider", table_name="user_accounts")
    op.drop_column("user_accounts", "last_login_at")
    op.drop_column("user_accounts", "external_subject")
    op.drop_column("user_accounts", "auth_provider")
