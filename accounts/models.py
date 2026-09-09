from datetime import date
import mimetypes

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



class User(AbstractUser):
    must_change_pw = models.BooleanField(default=False)
    phone = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return self.get_username()


class InviteToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"{self.user.username} ({'использован' if self.used_at else 'активен'})"


def doc_upload_to(instance: "DocumentFile", filename: str) -> str:
    oid = instance.document.owner_id or "unknown"
    kind = (instance.document.kind or Document.Kind.PERSONAL).lower()
    return f"docs/{oid}/{kind}/{filename}"


class Document(models.Model):

    class Kind(models.TextChoices):
        PERSONAL = "personal", _("Личные")
        BUSINESS = "business", _("Разрешения/лицензии")
        DOZVOL   = "dozvol",   _("Дозвол")

    title = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.PERSONAL,   # <---- исправлено
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
        db_index=True,
    )

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < date.today())

    def __str__(self) -> str:
        return self.title

    class Meta:
        ordering = ["-updated_at", "id"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "-updated_at"]),
            models.Index(fields=["kind"]),
            models.Index(fields=["expires_at"]),
        ]


class DocumentFile(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=doc_upload_to)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.split("/")[-1]

    @property
    def content_type(self):
        guess, _ = mimetypes.guess_type(self.file.name)
        return guess or "application/octet-stream"

    def __str__(self) -> str:
        return self.filename
