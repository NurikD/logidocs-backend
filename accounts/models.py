from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    must_change_pw = models.BooleanField(default=False)  # принудительная смена при первом входе
