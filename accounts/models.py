from datetime import date
import mimetypes

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    must_change_pw = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.get_username()


def doc_upload_to(instance: "Document", filename: str) -> str:
    """
    Путь хранения: docs/<owner_id>/<kind>/<filename>
    Не трогаем имя файла, если нужна нормализация — делайте её при загрузке.
    """
    oid = instance.owner_id or "unknown"
    kind = (instance.kind or Document.Kind.OTHER).lower()
    return f"docs/{oid}/{kind}/{filename}"


class Document(models.Model):
    class Kind(models.TextChoices):
        LICENSE = "license", _("Лицензия")
        PERMIT  = "permit",  _("Разрешение")
        POLICY  = "policy",  _("Полис")
        CERT    = "cert",    _("Сертификат")
        OTHER   = "other",   _("Другое")

    # --- основные поля ---
    title = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.OTHER,
        db_index=True,  # частый фильтр — индексируем
    )
    file = models.FileField(upload_to=doc_upload_to, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
        # FK в Postgres и так индексируется, но явно не мешает:
        db_index=True,
    )

    # --- служебные методы/свойства ---
    def replace_file(self, new_file) -> None:
        """Заменяет файл без ведения версий."""
        self.file = new_file

    @property
    def filename(self) -> str | None:
        return self.file.name.split("/")[-1] if self.file else None

    @property
    def content_type(self) -> str | None:
        if not self.file:
            return None
        guess, _ = mimetypes.guess_type(self.file.name)
        return guess or "application/octet-stream"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < date.today())

    def __str__(self) -> str:
        return self.title

    class Meta:
        # Часто открываем последние изменения — ускорит сортировку по умолчанию
        ordering = ["-updated_at", "id"]

        # Прицельные индексы под типовые запросы:
        indexes = [
            # Частейший кейс: документы конкретного пользователя + фильтр по активности
            models.Index(fields=["owner", "is_active"], name="doc_owner_active_idx"),
            # Списки по пользователю с сортировкой по дате обновления
            models.Index(fields=["owner", "-updated_at"], name="doc_owner_updated_idx"),
            # Фильтры по типу документа
            models.Index(fields=["kind"], name="doc_kind_idx"),
            # Поиск просроченных/скоро истекающих
            models.Index(fields=["expires_at"], name="doc_expires_idx"),
        ]
