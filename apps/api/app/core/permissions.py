import enum
from typing import Dict, List

from app.models.organization_membership import MembershipRole


class Permission(str, enum.Enum):
    UPDATE_ORGANIZATION = "update_organization"
    DELETE_ORGANIZATION = "delete_organization"
    ADD_MEMBER = "add_member"
    VIEW_MEMBERS = "view_members"
    UPDATE_MEMBER_ROLE = "update_member_role"
    REMOVE_MEMBER = "remove_member"


ROLE_PERMISSIONS: Dict[MembershipRole, List[Permission]] = {
    MembershipRole.owner: [
        Permission.UPDATE_ORGANIZATION,
        Permission.DELETE_ORGANIZATION,
        Permission.ADD_MEMBER,
        Permission.VIEW_MEMBERS,
        Permission.UPDATE_MEMBER_ROLE,
        Permission.REMOVE_MEMBER,
    ],
    MembershipRole.admin: [
        Permission.UPDATE_ORGANIZATION,
        Permission.ADD_MEMBER,
        Permission.VIEW_MEMBERS,
        Permission.REMOVE_MEMBER,
    ],
    MembershipRole.member: [
        Permission.VIEW_MEMBERS,
    ],
}


def has_permission(role: MembershipRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])
