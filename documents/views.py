from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Document
from .serializers import DocumentSerializer

class DocumentListView(ListAPIView):
    queryset = Document.objects.all().order_by("title")
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
