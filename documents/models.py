from django.conf import settings
from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to="docs/", null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ВЛАДЕЛЕЦ (один к одному пользователю)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,      # чтобы нельзя было удалить пользователя с документами
        related_name="documents",
        null=True, blank=True,         # сначала разрешим null, затем можно ужесточить
        help_text="Пользователь-владелец документа",
    )

    def replace_file(self, new_file):
        self.file = new_file
        self.version = (self.version or 0) + 1

    def __str__(self):
        return f"{self.title} (v{self.version})"
