from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, get_object_or_404
from django.http import FileResponse
from .models import Document
from .serializers import DocumentSerializer

class DocumentListAPI(ListAPIView):
    queryset = Document.objects.all().order_by("title")
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

class DocumentDownloadAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        f = doc.file.open("rb")
        return FileResponse(
            f, as_attachment=False, filename=doc.file.name.split("/")[-1],
            content_type="application/pdf"
        )

class DocumentReplaceAPI(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        """
        Форм-data: file=<pdf>, title?=..., type?=..., expires_at?=YYYY-MM-DD
        Меняет файл и увеличивает version. Остальные поля — опционально.
        """
        doc = get_object_or_404(Document, pk=pk)
        file = request.FILES.get("file")
        if file:
            doc.replace_file(file)
        if "title" in request.data: doc.title = request.data["title"]
        if "type" in request.data: doc.type = request.data["type"]
        if "expires_at" in request.data: doc.expires_at = request.data["expires_at"] or None
        doc.save()
        return Response({"ok": True, "version": doc.version})

class DocumentDeleteAPI(APIView):
    permission_classes = [IsAdminUser]
    def delete(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        doc.delete()
        return Response({"ok": True})
