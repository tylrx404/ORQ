"""add models table

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-08-04 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e7f8a9b0c1d'
down_revision: Union[str, None] = '5d6e7f8a9b0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'models',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('model_identifier', sa.String(length=255), nullable=False),
        sa.Column('context_window', sa.Integer(), nullable=True),
        sa.Column('max_output_tokens', sa.Integer(), nullable=True),
        sa.Column('supports_streaming', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('supports_tools', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('supports_vision', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('supports_reasoning', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id', 'model_identifier', name='uq_provider_model_identifier'),
    )
    op.create_index(op.f('ix_models_provider_id'), 'models', ['provider_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_models_provider_id'), table_name='models')
    op.drop_table('models')
