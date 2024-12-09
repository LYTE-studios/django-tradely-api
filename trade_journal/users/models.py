from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class CustomUser(AbstractUser):
    # Any additional fields can go here
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)