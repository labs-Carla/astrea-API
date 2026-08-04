"""crea tabla cartas natales base, migracion faltante en el historial

Revision ID: cd41b1f78898
Revises:
Create Date: 2026-08-04 12:21:27.250687

Esta migracion no existia: la tabla cartas_natales se creaba historicamente
via Base.metadata.create_all() en main.py, y esa creacion inicial nunca
quedo capturada como migracion de Alembic. La cadena arrancaba en
ebe4e784d7ff, que ya asume que la tabla existe (solo la altera) -- corriendo
"alembic upgrade head" sobre una base de datos nueva, sin create_all()
ejecutado antes, la migracion ebe4e784d7ff falla con NoSuchTableError.

Esta migracion recrea el schema exacto que tenia la tabla antes de
ebe4e784d7ff (verificado contra una copia de produccion de esa epoca:
astrea_prod_copy.db), para que la cadena completa de Alembic pueda
reproducir el schema actual desde cero, sin depender de create_all().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd41b1f78898'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cartas_natales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha_hora_local', sa.DateTime(), nullable=False),
        sa.Column('latitud', sa.Float(), nullable=False),
        sa.Column('longitud', sa.Float(), nullable=False),
        sa.Column('calculo_json', sa.Text(), nullable=False),
        sa.Column('interpretacion_json', sa.Text(), nullable=False),
        sa.Column('fecha_generacion', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('cartas_natales', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cartas_natales_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_cartas_natales_fecha_hora_local'), ['fecha_hora_local'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('cartas_natales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cartas_natales_fecha_hora_local'))
        batch_op.drop_index(batch_op.f('ix_cartas_natales_id'))
    op.drop_table('cartas_natales')
