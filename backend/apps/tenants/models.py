import uuid

from django.db import models


class Tenant(models.Model):
    """A professional firm. Root of every isolation boundary.

    Phase 1 only declares identity so other apps can reference it; plan,
    status and data-residency fields arrive in Phase 3.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=63, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
