import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(default=uuid.uuid4)
    tg_id = models.IntegerField(unique=True)
    is_trainer=models.BooleanField(default=False)
    USERNAME_FIELD = "tg_id"
    REQUIRED_FIELDS = ["username"]
    def __str__(self) -> str:
        return self.first_name

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"