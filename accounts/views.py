from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.views import APIView
from rest_framework import status

from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.views import TokenObtainPairView
from django.http import FileResponse, Http404

from .models import User, Document, DocumentFile
from .serializers import LoginSerializer, ChangePasswordSerializer, DocumentSerializer

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
    return Document.objects.select_related("owner").prefetch_related("files")


class DocumentListAPI(ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        return qs_with_owner().order_by("title") if u.is_superuser else qs_with_owner().filter(owner=u).order_by("title")


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



