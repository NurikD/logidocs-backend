import os

from rest_framework.permissions import IsAuthenticated, IsAdminUser, BasePermission
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.views import APIView
from rest_framework import status

from django.contrib.auth.hashers import check_password
from django.db.models import Count
from rest_framework_simplejwt.views import TokenObtainPairView
from django.http import FileResponse, Http404, HttpResponse

from .models import User, Document, DocumentFile, InviteToken, Vehicle, DeviceToken
from .serializers import (
    LoginSerializer, ChangePasswordSerializer, DocumentSerializer, VehicleSerializer,
    DeviceTokenSerializer, ExpiringDocumentSerializer,
)

from .forms import SetPasswordFormWithoutOldPassword
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user: User = request.user
        if not check_password(s.validated_data["old_password"], user.password):
            return Response({"detail": "Неверный старый пароль"}, status=400)
        user.set_password(s.validated_data["new_password"])
        user.must_change_pw = False
        user.save(update_fields=["password", "must_change_pw"])
        return Response({"ok": True})


def qs_with_owner():
    return Document.objects.select_related("owner", "vehicle").prefetch_related("files")


class VehicleListAPI(ListAPIView):
    """Автомобили текущего пользователя. Пустой список — клиент с одной машиной,
    документы приходят прямо в /api/documents/ без папок."""
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = Vehicle.objects.all() if u.is_superuser else Vehicle.objects.filter(owner=u)
        return qs.annotate(documents_count=Count("documents")).order_by("plate")


class DocumentListAPI(ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = qs_with_owner().order_by("title") if u.is_superuser else qs_with_owner().filter(owner=u).order_by("title")

        vehicle_param = self.request.query_params.get("vehicle")
        if vehicle_param == "none":
            qs = qs.filter(vehicle__isnull=True)
        elif vehicle_param:
            qs = qs.filter(vehicle_id=vehicle_param)
        return qs


class DocumentDetailAPI(RetrieveAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    queryset = qs_with_owner()

    def get_object(self):
        obj = super().get_object()
        u = self.request.user
        if u.is_superuser or obj.owner_id == u.id:
            return obj
        raise Http404


class DocumentFileDownloadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, file_pk):
        df = get_object_or_404(DocumentFile.objects.select_related("document__owner"), pk=file_pk)
        doc = df.document
        u = request.user
        if not (u.is_superuser or doc.owner_id == u.id):
            raise Http404

        return FileResponse(
            df.file.open("rb"),
            as_attachment=False,
            filename=df.filename,
            content_type=df.content_type,
        )


class DocumentReplaceAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)

        # обновление полей документа
        if "title" in request.data:
            doc.title = request.data["title"]

        if "kind" in request.data:
            doc.kind = request.data["kind"]

        if "is_active" in request.data:
            doc.is_active = bool(int(request.data["is_active"])) if isinstance(request.data["is_active"], str) else bool(request.data["is_active"])

        if "expires_at" in request.data:
            doc.expires_at = request.data["expires_at"] or None

        if "owner_id" in request.data:
            doc.owner_id = request.data.get("owner_id") or None

        doc.save()
        return Response({"ok": True})


class DocumentDeleteAPI(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        doc.delete()
        return Response({"ok": True})


class DeviceRegisterAPI(APIView):
    """Регистрация FCM-токена устройства за текущим пользователем."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = DeviceTokenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        DeviceToken.objects.update_or_create(
            token=s.validated_data["token"],
            defaults={"user": request.user, "platform": s.validated_data["platform"]},
        )
        return Response({"ok": True})


class DocumentDismissNotificationAPI(APIView):
    """Клиент нажал «Понятно» — больше не напоминаем по этому документу."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        u = request.user
        if not (u.is_superuser or doc.owner_id == u.id):
            raise Http404
        doc.notification_dismissed = True
        doc.save(update_fields=["notification_dismissed"])
        return Response({"ok": True})


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class DocumentExpiringListAPI(ListAPIView):
    """Экран диспетчера: путёвки всех клиентов, которые скоро истекут или истекли."""
    serializer_class = ExpiringDocumentSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        qs = (Document.objects
              .filter(kind=Document.Kind.BUSINESS, expires_at__isnull=False)
              .select_related("owner", "vehicle")
              .order_by("expires_at"))
        return [d for d in qs if d.is_expired or d.is_expiring_soon]


def cron_send_expiry_notifications(request):
    """Внешний триггер ежедневной рассылки push (see management/commands/
    send_expiry_notifications.py).

    Бесплатный тариф PythonAnywhere не даёт Scheduled Tasks — расписание
    держит внешний cron-сервис, который раз в сутки дёргает этот URL.
    Секрет в query-параметре, а не в пути, чтобы не светился в логах веб-сервера
    построчно с самим доменом; сравнение constant-time, чтобы не утекало
    через тайминг. Без верного секрета — обычный 404, а не 403: посторонний
    не должен даже понять, что по этому адресу что-то есть.
    """
    import hmac
    from io import StringIO
    from django.core.management import call_command

    secret = os.environ.get("CRON_SECRET")
    if not secret or not hmac.compare_digest(request.GET.get("key", ""), secret):
        raise Http404

    out = StringIO()
    call_command("send_expiry_notifications", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain; charset=utf-8")


def set_password_view(request, token):
    invite = get_object_or_404(InviteToken.objects.select_related("user"), token=token)

    if not invite.is_valid:
        return render(request, "accounts/set_password.html", {"invalid": True})

    if request.method == "POST":
        form = SetPasswordFormWithoutOldPassword(request.POST)
        if form.is_valid():
            user = invite.user
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.must_change_pw = False
            user.save(update_fields=["password", "is_active", "must_change_pw"])
            invite.used_at = timezone.now()
            invite.save(update_fields=["used_at"])
            return render(request, "accounts/set_password.html", {"success": True, "username": user.username})
    else:
        form = SetPasswordFormWithoutOldPassword()

    return render(request, "accounts/set_password.html", {"form": form, "invite": invite})



