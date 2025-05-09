"""empty message.

Revision ID: 9a6155f8c232
Revises: 3d1949e339cc
Create Date: 2025-05-09 08:21:20.596113

"""

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "9a6155f8c232"
down_revision = "3d1949e339cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Run the migration."""
    op.execute(
        text("CREATE INDEX ON document_index USING hnsw (embedding vector_l2_ops);")
    )


def downgrade() -> None:
    """Undo the migration."""
