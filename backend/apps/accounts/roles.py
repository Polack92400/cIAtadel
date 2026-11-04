from django.db import models


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer (read-only)"


RANK = {Role.VIEWER: 10, Role.MEMBER: 20, Role.ADMIN: 30, Role.OWNER: 40}


def role_at_least(role: str, minimum: str) -> bool:
    return RANK.get(role, 0) >= RANK[minimum]
