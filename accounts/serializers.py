from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, Document, DocumentFile, Vehicle, DeviceToken


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
        # приложение по этому флагу решает, показать клиентский экран
        # или экран диспетчера со списком истекающих путёвок
        data["is_superuser"] = user.is_superuser
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


class VehicleSerializer(serializers.ModelSerializer):
    documents_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Vehicle
        fields = ["id", "plate", "documents_count"]


class DocumentSerializer(serializers.ModelSerializer):
    files = DocumentFileSerializer(many=True, read_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    # null у клиентов с одной машиной — документы висят прямо на пользователе
    vehicle_id = serializers.IntegerField(source="vehicle.id", read_only=True, default=None)
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True, default=None)

    class Meta:
        model = Document
        fields = [
            "id", "title", "kind", "is_active", "issued_at", "expires_at",
            "updated_at", "owner_id", "vehicle_id", "vehicle_plate", "files",
            "is_expired", "is_expiring_soon", "notification_dismissed",
        ]


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["token", "platform"]


class ExpiringDocumentSerializer(serializers.ModelSerializer):
    """Для экрана диспетчера: чья путёвка, по какой машине и как с человеком связаться."""
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_phone = serializers.CharField(source="owner.phone", read_only=True, default="")
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True, default=None)

    class Meta:
        model = Document
        fields = [
            "id", "title", "expires_at", "is_expired", "is_expiring_soon",
            "owner_id", "owner_username", "owner_name", "owner_phone", "vehicle_plate",
        ]

    def get_owner_name(self, obj):
        if not obj.owner:
            return ""
        return f"{obj.owner.last_name} {obj.owner.first_name}".strip()
