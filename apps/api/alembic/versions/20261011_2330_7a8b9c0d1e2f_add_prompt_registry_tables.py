"""add prompt registry tables

Revision ID: 7a8b9c0d1e2f
Revises: 3311c5eb7a21
Create Date: 2026-10-11 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, None] = '3311c5eb7a21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create prompts table without the published_version_id foreign key constraint to break circular dependency
    op.create_table(
        'prompts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_version_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_prompts_organization_id_name'),
    )
    op.create_index(op.f('ix_prompts_organization_id'), 'prompts', ['organization_id'], unique=False)

    # 2. Create prompt_versions table with foreign key referencing prompts.id
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('prompt_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prompt_id', 'version_number', name='uq_prompt_versions_prompt_id_version_number'),
    )
    op.create_index(op.f('ix_prompt_versions_prompt_id'), 'prompt_versions', ['prompt_id'], unique=False)

    # 3. Safely add foreign key from prompts.published_version_id to prompt_versions.id
    op.create_foreign_key(
        'fk_prompts_published_version_id',
        'prompts',
        'prompt_versions',
        ['published_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # 1. Drop foreign key constraint first
    op.drop_constraint('fk_prompts_published_version_id', 'prompts', type_='foreignkey')

    # 2. Drop prompt_versions table
    op.drop_index(op.f('ix_prompt_versions_prompt_id'), table_name='prompt_versions')
    op.drop_table('prompt_versions')

    # 3. Drop prompts table
    op.drop_index(op.f('ix_prompts_organization_id'), table_name='prompts')
    op.drop_table('prompts')
