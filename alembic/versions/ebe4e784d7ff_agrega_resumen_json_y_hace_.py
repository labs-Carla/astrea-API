"""agrega resumen_json y hace interpretacion_json nullable

Revision ID: ebe4e784d7ff
Revises: 
Create Date: 2026-07-16 12:28:19.791720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebe4e784d7ff'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cartas_natales') as batch_op:
        batch_op.add_column(sa.Column('resumen_json', sa.Text(), nullable=True))
        batch_op.alter_column('interpretacion_json',
                   existing_type=sa.TEXT(),
                   nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('cartas_natales') as batch_op:
        batch_op.alter_column('interpretacion_json',
                   existing_type=sa.TEXT(),
                   nullable=False)
        batch_op.drop_column('resumen_json')
