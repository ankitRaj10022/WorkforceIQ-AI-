"""add refresh-token session state

Revision ID: 0002_session_refresh_tokens
Revises: 0001_industry_schema
Create Date: 2026-05-11
"""
from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0002_session_refresh_tokens"
down_revision = "0001_industry_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("session_uuid", sa.String(length=36), nullable=True))
    op.add_column("user_sessions", sa.Column("refresh_token_jti", sa.String(length=36), nullable=True))
    op.add_column("user_sessions", sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_sessions", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_sessions", sa.Column("revoked_reason", sa.String(length=128), nullable=True))

    bind = op.get_bind()
    session_table = sa.table(
        "user_sessions",
        sa.column("id", sa.Integer()),
        sa.column("session_uuid", sa.String(length=36)),
    )
    rows = bind.execute(sa.select(session_table.c.id).where(session_table.c.session_uuid.is_(None))).all()
    for row in rows:
        bind.execute(
            session_table.update()
            .where(session_table.c.id == row.id)
            .values(session_uuid=str(uuid4()))
        )

    op.alter_column("user_sessions", "session_uuid", existing_type=sa.String(length=36), nullable=False)
    op.create_index("ix_user_sessions_session_uuid", "user_sessions", ["session_uuid"], unique=True)
    op.create_index("ix_user_sessions_refresh_token_jti", "user_sessions", ["refresh_token_jti"], unique=True)
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_jti", table_name="user_sessions")
    op.drop_index("ix_user_sessions_session_uuid", table_name="user_sessions")
    op.drop_column("user_sessions", "revoked_reason")
    op.drop_column("user_sessions", "revoked_at")
    op.drop_column("user_sessions", "refresh_expires_at")
    op.drop_column("user_sessions", "refresh_token_jti")
    op.drop_column("user_sessions", "session_uuid")
