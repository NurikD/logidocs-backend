from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, get_object_or_404
from django.http import FileResponse, Http404

from .models import Document
from .serializers import DocumentSerializer
# documents/views.py
from rest_framework.generics import RetrieveAPIView
class DocumentDetailAPI(RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not (user.is_superuser or obj.owner_id == user.id):
            raise Http404
        return obj


class DocumentListAPI(ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # ВАЖНО: только суперюзер видит все
        if user.is_superuser:
            return Document.objects.all().order_by("title")
        return Document.objects.filter(owner=user).order_by("title")


class DocumentDownloadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        user = request.user
        if not (user.is_superuser or doc.owner_id == user.id):
            raise Http404
        if not doc.file:
            raise Http404
        f = doc.file.open("rb")
        return FileResponse(
            f,
            as_attachment=False,
            filename=doc.file.name.split("/")[-1],
            content_type="application/pdf",
        )


class DocumentReplaceAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        file = request.FILES.get("file")
        if file:
            doc.replace_file(file)
        if "title" in request.data: doc.title = request.data["title"]
        if "type" in request.data: doc.type = request.data["type"]
        if "expires_at" in request.data: doc.expires_at = request.data["expires_at"] or None
        if "owner_id" in request.data: doc.owner_id = request.data.get("owner_id") or None
        doc.save()
        return Response({"ok": True, "version": doc.version})

class DocumentDeleteAPI(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        get_object_or_404(Document, pk=pk).delete()
        return Response({"ok": True})
