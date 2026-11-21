"""custom workflows: user-described routines compiled into workflow specs

Revision ID: c7e2d91a4f60
Revises: a1f3c9e2b7d4
Create Date: 2026-11-22 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e2d91a4f60"
down_revision: Union[str, Sequence[str], None] = "a1f3c9e2b7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_workflows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("when", sa.String(length=240), nullable=False),
        sa.Column("examples", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("checklist", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("source_prompt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_workflows_workspace_id", "custom_workflows", ["workspace_id"])
    op.create_index("ix_custom_workflows_owner_user_id", "custom_workflows", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_custom_workflows_owner_user_id", table_name="custom_workflows")
    op.drop_index("ix_custom_workflows_workspace_id", table_name="custom_workflows")
    op.drop_table("custom_workflows")
