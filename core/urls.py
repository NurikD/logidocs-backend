from django import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin
from accounts.views import LoginView, DocumentFileDownloadAPI # твой TokenObtainPairView кастомный

from accounts.views import (
    LoginView, ChangePasswordView,
    DocumentListAPI, DocumentDetailAPI,
    DocumentReplaceAPI, DocumentDeleteAPI,
    VehicleListAPI, DeviceRegisterAPI,
    DocumentDismissNotificationAPI,
    set_password_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # auth
    path("api/auth/token/", LoginView.as_view()),
    path("api/auth/change-password/", ChangePasswordView.as_view()),

    path("api/vehicles/", VehicleListAPI.as_view()),
    path("api/devices/register/", DeviceRegisterAPI.as_view()),
    path("api/documents/", DocumentListAPI.as_view()),
    path("api/documents/<int:pk>/dismiss-notification/", DocumentDismissNotificationAPI.as_view()),
    path("api/documents/<int:pk>/", DocumentDetailAPI.as_view()),
    # Новый URL для скачивания конкретного файла
    path("api/documents/<int:pk>/replace/", DocumentReplaceAPI.as_view()),
    path("api/documents/<int:pk>/delete/", DocumentDeleteAPI.as_view()),
    path("api/documents/<int:pk>/download/<int:file_pk>/", DocumentFileDownloadAPI.as_view()),
    path("admin-ui/", include("adminui.urls", namespace="adminui")),

    path("set-password/<str:token>/", set_password_view, name="set_password"),
]

# Медиа отдаём напрямую только в dev — в проде файлы должны идти через
# авторизованные вьюхи (DocumentFileDownloadAPI / adminui.document_file_serve).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)