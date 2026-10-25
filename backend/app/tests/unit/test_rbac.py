from app.core.permissions import can_grant_role, can_manage_member, role_at_least
from app.models.enums import WorkspaceRole


def test_role_ordering():
    assert role_at_least(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    assert role_at_least(WorkspaceRole.MEMBER, WorkspaceRole.VIEWER)
    assert not role_at_least(WorkspaceRole.VIEWER, WorkspaceRole.MEMBER)


def test_roles_cannot_be_granted_above_actor():
    assert can_grant_role(WorkspaceRole.OWNER, WorkspaceRole.OWNER)
    assert can_grant_role(WorkspaceRole.ADMIN, WorkspaceRole.MEMBER)
    assert not can_grant_role(WorkspaceRole.ADMIN, WorkspaceRole.OWNER)
    assert can_grant_role(WorkspaceRole.MEMBER, WorkspaceRole.VIEWER)
    assert not can_grant_role(WorkspaceRole.VIEWER, WorkspaceRole.MEMBER)


def test_member_management_requires_admin_or_owner_and_sufficient_rank():
    assert can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.MEMBER)
    assert not can_manage_member(WorkspaceRole.ADMIN, WorkspaceRole.OWNER)
    assert not can_manage_member(WorkspaceRole.MEMBER, WorkspaceRole.VIEWER)
