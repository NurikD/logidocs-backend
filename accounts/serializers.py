from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import Document

class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        # можно вернуть для админ-UI, но фронт его игнорирует
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

class DocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id","title","kind", "is_active","expires_at",
            "file_name","content_type","size","owner_id","file_url",
        ]

    def get_file_name(self, obj): return obj.filename
    def get_content_type(self, obj): return obj.content_type
    def get_size(self, obj):
        try: return obj.file.size if obj.file else None
        except Exception: return None
    def get_file_url(self, obj):
        req = self.context.get("request")
        if not (req and obj.file): return None
        return req.build_absolute_uri(f"/api/documents/{obj.pk}/download/")
