from django.contrib import admin
from django.urls import path
from accounts.views import LoginView, ChangePasswordView
from documents.views import DocumentListView

urlpatterns = [
    path('admin/', admin.site.urls),

    # auth
    path('api/auth/token/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/auth/change-password/', ChangePasswordView.as_view()),

    # docs
    path('api/documents/', DocumentListView.as_view()),
]
