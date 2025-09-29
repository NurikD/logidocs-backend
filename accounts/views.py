from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.views import APIView
from rest_framework import status

from django.contrib.auth.hashers import check_password
from .serializers import LoginSerializer, ChangePasswordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Document
from django.http import FileResponse, Http404
from .serializers import DocumentSerializer

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
    return Document.objects.select_related("owner")

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

# accounts/views.py
class DocumentDownloadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(Document.objects.select_related("owner"), pk=pk)
        u = request.user
        if not (u.is_superuser or doc.owner_id == u.id):
            raise Http404  # чужое — скрываем факт существования

        if not doc.file:
            # вместо голого 404 вернём JSON с пояснением
            return Response({"detail": "К документу не прикреплён файл."}, status=404)

        return FileResponse(
            doc.file.open("rb"),
            as_attachment=False,
            filename=doc.filename or "document",
            content_type=doc.content_type or "application/octet-stream",
        )


class DocumentReplaceAPI(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        f = request.FILES.get("file")
        if f: doc.replace_file(f)
        if "title" in request.data: doc.title = request.data["title"]
        if "kind" in request.data: doc.kind = request.data["kind"]
        if "is_active" in request.data: doc.is_active = bool(int(request.data["is_active"])) if isinstance(request.data["is_active"], str) else bool(request.data["is_active"])
        if "expires_at" in request.data: doc.expires_at = request.data["expires_at"] or None
        if "owner_id" in request.data: doc.owner_id = request.data.get("owner_id") or None
        doc.save()
        return Response({"ok": True, "version": doc.version})

class DocumentDeleteAPI(APIView):
    permission_classes = [IsAdminUser]
    def delete(self, request, pk):
        get_object_or_404(Document, pk=pk).delete()
        return Response({"ok": True})