import secrets
import string

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for Haranogiyeche.

    AbstractUser already provides: username, password (stored hashed),
    first_name, last_name, is_staff, is_active, date_joined.
    Django adds the primary key (id) automatically; it plays the role of user_id.
    We only override email so it is required and unique.
    """

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username


def generate_join_code(length=8):
    """Random, hard-to-guess code such as 'K7QX2M9A' (no look-alike characters)."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Community(models.Model):
    """
    A university, organization or local group.
    Knowing the join_code only lets a LOGGED-IN user request to join;
    it never gives access to the community's posts by itself.
    """

    name = models.CharField(max_length=150)
    join_code = models.CharField(max_length=12, unique=True, editable=False)
    qr_code = models.ImageField(upload_to="community_qr/", blank=True, null=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="administered_communities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "communities"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Create a unique join code the first time the community is saved.
        if not self.join_code:
            code = generate_join_code()
            while Community.objects.filter(join_code=code).exists():
                code = generate_join_code()
            self.join_code = code

        is_new = self._state.adding
        super().save(*args, **kwargs)

        # The creator automatically becomes the community's admin member.
        if is_new:
            Membership.objects.get_or_create(
                user=self.admin,
                community=self,
                defaults={"role": Membership.Role.ADMIN},
            )


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MODERATOR = "moderator", "Moderator"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A user cannot have two memberships in the same community.
            models.UniqueConstraint(
                fields=["user", "community"], name="unique_user_community_membership"
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.community} ({self.role})"