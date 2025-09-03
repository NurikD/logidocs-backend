from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=64, blank=True)
    version = models.IntegerField(default=1)
    expires_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title
