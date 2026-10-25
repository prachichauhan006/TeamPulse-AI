from app.models.enums import WorkspaceRole

ROLE_ORDER = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.MEMBER: 2,
    WorkspaceRole.ADMIN: 3,
    WorkspaceRole.OWNER: 4,
}


def role_at_least(role: WorkspaceRole, minimum: WorkspaceRole) -> bool:
    return ROLE_ORDER[role] >= ROLE_ORDER[minimum]


def can_grant_role(actor_role: WorkspaceRole, target_role: WorkspaceRole) -> bool:
    return ROLE_ORDER[actor_role] >= ROLE_ORDER[target_role]


def can_manage_member(actor_role: WorkspaceRole, target_role: WorkspaceRole) -> bool:
    return actor_role in {WorkspaceRole.OWNER, WorkspaceRole.ADMIN} and can_grant_role(
        actor_role, target_role
    )
