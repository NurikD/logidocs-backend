from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, Document, DocumentFile


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data["must_change_pw"] = user.must_change_pw
        data["username"] = user.username
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        validate_password(value)
        if len(value) < 10:
            raise serializers.ValidationError("Пароль слишком короткий (>=10).")
        return value


class DocumentFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFile
        fields = ["id", "file_name", "content_type", "size", "uploaded_at"]

    def get_file_name(self, obj): return obj.filename
    def get_content_type(self, obj): return obj.content_type
    def get_size(self, obj):
        try:
            return obj.file.size if obj.file else None
        except Exception:
            return None


class DocumentSerializer(serializers.ModelSerializer):
    files = DocumentFileSerializer(many=True, read_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "title", "kind", "is_active", "expires_at",
            "updated_at", "owner_id", "files", "is_expired"
        ]
