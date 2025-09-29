from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import mimetypes
from datetime import date

class User(AbstractUser):
    must_change_pw = models.BooleanField(default=False)

def doc_upload_to(instance, filename):
    oid = instance.owner_id or "unknown"
    kind = (instance.kind or "other").lower()
    return f"docs/{oid}/{kind}/{filename}"

class Document(models.Model):
    class Kind(models.TextChoices):
        LICENSE = "license", "Лицензия"
        PERMIT  = "permit",  "Разрешение"
        POLICY  = "policy",  "Полис"
        CERT    = "cert",    "Сертификат"
        OTHER   = "other",   "Другое"

    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.OTHER)
    file = models.FileField(upload_to=doc_upload_to, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True, blank=True
    )

    def replace_file(self, new_file):
        self.file = new_file  # версий больше нет

    @property
    def filename(self):
        return self.file.name.split("/")[-1] if self.file else None

    @property
    def content_type(self):
        if not self.file:
            return None
        guess, _ = mimetypes.guess_type(self.file.name)
        return guess or "application/octet-stream"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < date.today())

    def __str__(self):
        return self.title
