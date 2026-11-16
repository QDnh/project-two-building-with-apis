from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A reader. Signs in by username; the email must be unique."""

    email = models.EmailField("email address", unique=True)
