from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from accounts.views import LoginView  # твой TokenObtainPairView кастомный

from accounts.views import (
    LoginView, ChangePasswordView,
    DocumentListAPI, DocumentDetailAPI, DocumentDownloadAPI,
    DocumentReplaceAPI, DocumentDeleteAPI,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # auth
    path("api/auth/token/", LoginView.as_view()),
    path("api/auth/change-password/", ChangePasswordView.as_view()),

    path("api/documents/", DocumentListAPI.as_view()),
    path("api/documents/<int:pk>/", DocumentDetailAPI.as_view()),
    path("api/documents/<int:pk>/download/", DocumentDownloadAPI.as_view()),
    path("api/documents/<int:pk>/replace/", DocumentReplaceAPI.as_view()),
    path("api/documents/<int:pk>/delete/", DocumentDeleteAPI.as_view()),

    # admin only
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # только для dev
