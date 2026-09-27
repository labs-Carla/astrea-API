"""agrega pago_confirmado y fecha_confirmacion_pago a cartas_natales

Revision ID: b3c9e1f47a20
Revises: 71bee81d92ba
Create Date: 2026-09-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c9e1f47a20'
down_revision: Union[str, Sequence[str], None] = '71bee81d92ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('cartas_natales', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pago_confirmado', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('fecha_confirmacion_pago', sa.DateTime(), nullable=True))

    # Hasta ahora los datos de compra solo llegaban desde gracias.html,
    # DESPUES de pagar en Hotmart: toda carta con email ya esta pagada.
    op.execute(
        "UPDATE cartas_natales "
        "SET pago_confirmado = 1, fecha_confirmacion_pago = fecha_solicitud_compra "
        "WHERE email IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('cartas_natales', schema=None) as batch_op:
        batch_op.drop_column('fecha_confirmacion_pago')
        batch_op.drop_column('pago_confirmado')
