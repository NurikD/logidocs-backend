from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to="docs/", null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def replace_file(self, new_file):
        # при замене файла увеличиваем версию
        self.file = new_file
        self.version = (self.version or 0) + 1

    def __str__(self):
        return f"{self.title} (v{self.version})"
