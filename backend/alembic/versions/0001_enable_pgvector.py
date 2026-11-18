# migrations/versions/0001_enable_pgvector.py
from alembic import op

revision, down_revision = "0001", None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")