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