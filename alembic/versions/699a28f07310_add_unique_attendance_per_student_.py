"""add unique attendance per student session

Revision ID: 699a28f07310
Revises: 69f6ae7368a0
Create Date: 2026-10-03 02:21:30.481746

"""
from typing import Sequence, Union

from alembic import op



# revision identifiers, used by Alembic.
revision: str = '699a28f07310'
down_revision: Union[str, Sequence[str], None] = '69f6ae7368a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_attendance_student_session",
        "attendance",
        ["student_id", "class_session_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_attendance_student_session",
        table_name="attendance",
    )