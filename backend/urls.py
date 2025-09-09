from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from documents.views import DocumentListAPI, DocumentDownloadAPI, DocumentReplaceAPI, DocumentDeleteAPI, DocumentDetailAPI
from accounts.views import LoginView  # твой TokenObtainPairView кастомный

urlpatterns = [
    path("admin/", admin.site.urls),

    # auth
    path("api/auth/token/", LoginView.as_view()),

    # docs
    path("api/documents/", DocumentListAPI.as_view()),
    path("api/documents/<int:pk>/download/", DocumentDownloadAPI.as_view()),
    path("api/documents/<int:pk>/replace/", DocumentReplaceAPI.as_view()),  # admin only
    path("api/documents/<int:pk>/delete/", DocumentDeleteAPI.as_view()),
    path("api/documents/<int:pk>/", DocumentDetailAPI.as_view()),
    # admin only
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # только для dev
