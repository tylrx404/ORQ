"""add organization invitations table

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-08-02 12:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = "4c5d6e7f8a9b"
down_revision: Union[str, None] = "3b4c5d6e7f8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Step 1 — Create invitation_status_enum via idempotent raw DDL.
    #
    # Why not use SQLAlchemy's SchemaType hooks?
    #
    # When postgresql.ENUM(create_type=False) is passed to op.create_table(),
    # Alembic fires the before_create event for each column.  The handler is
    # NamedType._on_table_create (SQLAlchemy 2.0.51, named_types.py:113):
    #
    #   if (
    #       checkfirst
    #       or (not self.metadata and not kw.get("_is_metadata_operation", False))
    #   ) and not self._check_for_name_in_memos(checkfirst, kw):
    #       self.create(bind=bind, checkfirst=checkfirst)
    #
    # _check_for_name_in_memos() returns True (suppressing creation) only when
    # self.create_type is True AND the name has been seen in the runner memo.
    # When create_type=False it returns True immediately — but the outer
    # condition is only reached when create_type=False suppresses it, so the
    # object is never created at all.  This is correct for membership_role_enum
    # (already in the DB) but leaves no way to create invitation_status_enum
    # safely, because:
    #
    #   a) create_type=True  → CREATE TYPE fires without IF NOT EXISTS, so a
    #      leftover type from any prior failed migration causes DuplicateObject.
    #   b) create_type=False → type is never created automatically at all.
    #   c) ENUM.create(checkfirst=True) before op.create_table() → type is
    #      created, then op.create_table fires _on_table_create again (because
    #      the object has no MetaData), causing a second CREATE TYPE.
    #
    # Solution: use a PostgreSQL anonymous DO block that silently ignores
    # duplicate_object.  This is unconditionally idempotent across any number
    # of failed migration attempts.
    # -------------------------------------------------------------------------
    op.execute(sa.text(
        "DO $$ BEGIN "
        "  CREATE TYPE invitation_status_enum "
        "  AS ENUM ('pending', 'accepted', 'expired', 'revoked'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    ))

    # -------------------------------------------------------------------------
    # Step 2 — Reference both enum types with create_type=False.
    #
    # Now that invitation_status_enum exists in the DB (created above),
    # both ENUM objects carry create_type=False so _check_for_name_in_memos
    # returns True and _on_table_create is suppressed for both columns.
    # No additional CREATE TYPE statements are emitted by op.create_table.
    # -------------------------------------------------------------------------
    invitation_status_enum = ENUM(
        "pending",
        "accepted",
        "expired",
        "revoked",
        name="invitation_status_enum",
        create_type=False,   # type exists — do not create it again
    )

    membership_role_enum = ENUM(
        "owner",
        "admin",
        "member",
        name="membership_role_enum",
        create_type=False,   # type was created by the memberships migration
    )

    op.create_table(
        "organization_invitations",

        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),

        sa.Column(
            "organization_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "role",
            membership_role_enum,
            nullable=False,
            server_default=sa.text("'member'"),
        ),

        sa.Column(
            "token",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "status",
            invitation_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),

        sa.Column(
            "created_by",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "token",
            name="uq_organization_invitation_token",
        ),
    )

    op.create_index(
        op.f("ix_organization_invitations_email"),
        "organization_invitations",
        ["email"],
        unique=False,
    )

    op.create_index(
        op.f("ix_organization_invitations_token"),
        "organization_invitations",
        ["token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_invitations_token"),
        table_name="organization_invitations",
    )

    op.drop_index(
        op.f("ix_organization_invitations_email"),
        table_name="organization_invitations",
    )

    op.drop_table("organization_invitations")

    # Drop the type we explicitly created in upgrade().
    # Use raw DDL to mirror the idempotent creation above.
    op.execute(sa.text("DROP TYPE IF EXISTS invitation_status_enum;"))