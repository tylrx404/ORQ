"""add agent spec versions table and current_version_id

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-21 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9c0d1e2f3a4b'
down_revision: Union[str, None] = '8b9c0d1e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create agent_spec_versions table
    op.create_table(
        'agent_spec_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('agent_spec_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prompt_id', sa.UUID(), nullable=True),
        sa.Column('prompt_version_id', sa.UUID(), nullable=True),
        sa.Column('provider_id', sa.UUID(), nullable=True),
        sa.Column('model_id', sa.UUID(), nullable=True),
        sa.Column(
            'tool_identifiers',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'memory_policy',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_spec_id'], ['agent_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['prompt_version_id'], ['prompt_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_spec_id', 'version_number', name='uq_agent_spec_versions_agent_spec_id_version_number'),
    )
    op.create_index(op.f('ix_agent_spec_versions_agent_spec_id'), 'agent_spec_versions', ['agent_spec_id'], unique=False)

    # 2. Add current_version_id column to agent_specs
    op.add_column('agent_specs', sa.Column('current_version_id', sa.UUID(), nullable=True))

    # 3. Add foreign key constraint from agent_specs.current_version_id to agent_spec_versions.id
    op.create_foreign_key(
        'fk_agent_specs_current_version_id',
        'agent_specs',
        'agent_spec_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # 1. Drop foreign key constraint from agent_specs
    op.drop_constraint('fk_agent_specs_current_version_id', 'agent_specs', type_='foreignkey')

    # 2. Drop current_version_id column from agent_specs
    op.drop_column('agent_specs', 'current_version_id')

    # 3. Drop agent_spec_versions table
    op.drop_index(op.f('ix_agent_spec_versions_agent_spec_id'), table_name='agent_spec_versions')
    op.drop_table('agent_spec_versions')
