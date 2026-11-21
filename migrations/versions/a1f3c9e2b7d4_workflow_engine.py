"""workflow engine: conversation workflow state + escalations log

Revision ID: a1f3c9e2b7d4
Revises: 6d95b373d40e
Create Date: 2026-11-21 23:30:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1f3c9e2b7d4"
down_revision: Union[str, Sequence[str], None] = "6d95b373d40e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("workflow_state", postgresql.JSONB(astext_type=sa.Text()),
                                             server_default="{}", nullable=False))
    op.add_column("conversations", sa.Column("workflow_version", sa.Integer(), server_default="0", nullable=False))
    op.create_table(
        "escalations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("conversation_id", sa.String(length=40), nullable=False),
        sa.Column("workflow", sa.String(length=60), nullable=True),
        sa.Column("trigger", sa.String(length=200), nullable=False),
        sa.Column("utterance", sa.Text(), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("tools_used", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_escalations_workspace_id", "escalations", ["workspace_id"])
    op.create_index("ix_escalations_conversation_id", "escalations", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_escalations_conversation_id", table_name="escalations")
    op.drop_index("ix_escalations_workspace_id", table_name="escalations")
    op.drop_table("escalations")
    op.drop_column("conversations", "workflow_version")
    op.drop_column("conversations", "workflow_state")
