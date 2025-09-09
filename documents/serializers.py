# serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "type", "version", "expires_at",
            "file_name", "content_type", "size",
        ]

    def get_file_name(self, obj):
        return obj.file.name.split("/")[-1] if obj.file else None

    def get_content_type(self, obj):
        return getattr(obj.file, "file", None) and getattr(obj.file.file, "content_type", None)

    def get_size(self, obj):
        try:
            return obj.file.size
        except Exception:
            return None
