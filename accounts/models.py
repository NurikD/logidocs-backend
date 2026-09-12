from datetime import date, timedelta
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


class Vehicle(models.Model):
    """Автомобиль клиента. Опционально — только у клиентов с несколькими машинами."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    plate = models.CharField(max_length=32, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.plate


DOCUMENT_EXPIRY_WARNING_DAYS = 7


def doc_upload_to(instance: "DocumentFile", filename: str) -> str:
    doc = instance.document
    oid = doc.owner_id or "unknown"
    kind = (doc.kind or Document.Kind.BUSINESS).lower()
    if doc.vehicle_id:
        return f"docs/{oid}/{doc.vehicle_id}/{kind}/{filename}"
    return f"docs/{oid}/{kind}/{filename}"


class Document(models.Model):

    class Kind(models.TextChoices):
        BUSINESS = "business", _("Путевка")
        DOZVOL   = "dozvol",   _("Дозвол")

    title = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.BUSINESS,
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    # Дата оформления — вводит админ (сейчас актуально для kind=business).
    # Срок путёвки не фиксированный (2 или 3 месяца) — expires_at админ
    # тоже вводит сам, а не считаем автоматически.
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    # Клиент нажал "Понятно" на уведомлении об истечении — больше не напоминаем
    # именно по этому документу (диспетчер всё равно продолжает получать свой дайджест).
    notification_dismissed = models.BooleanField(default=False)
    # Дата последней отправки push по этому документу — чтобы ежедневная
    # команда не слала повторно, если её запустят дважды за день.
    last_notified_date = models.DateField(null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
        db_index=True,
    )

    # Заполняется только у клиентов с несколькими машинами — документ лежит
    # в папке конкретного автомобиля, а не прямо на пользователе.
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
        db_index=True,
    )

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < date.today())

    @property
    def is_expiring_soon(self) -> bool:
        if not self.expires_at or self.is_expired:
            return False
        return self.expires_at <= date.today() + timedelta(days=DOCUMENT_EXPIRY_WARNING_DAYS)

    def __str__(self) -> str:
        return self.title

    class Meta:
        ordering = ["-updated_at", "id"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "-updated_at"]),
            models.Index(fields=["vehicle"]),
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


class DeviceToken(models.Model):
    """FCM-токен устройства для push-уведомлений."""

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    token = models.CharField(max_length=255, unique=True, db_index=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.platform})"
