from django.urls import path
from . import views

app_name = "adminui"

urlpatterns = [
    path("users/", views.users_list, name="users_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("users/<int:user_id>/password-link/", views.password_reset_link, name="password_reset_link"),

    # автомобили (только у клиентов с несколькими машинами)
    path("users/<int:user_id>/vehicles/add/", views.vehicle_add, name="vehicle_add"),
    path("users/<int:user_id>/vehicles/unassigned/", views.vehicle_detail, name="vehicle_detail_unassigned"),
    path("users/<int:user_id>/vehicles/<int:vehicle_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("users/<int:user_id>/vehicles/<int:vehicle_id>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("users/<int:user_id>/vehicles/<int:vehicle_id>/docs/<str:kind>/", views.vehicle_docs_list, name="vehicle_docs_list"),
    path("users/<int:user_id>/vehicles/<int:vehicle_id>/documents/<int:doc_id>/view/", views.document_view, name="vehicle_document_view"),
    path("users/<int:user_id>/vehicles/<int:vehicle_id>/documents/<int:doc_id>/files/<int:file_id>/view/", views.document_file_serve, name="vehicle_document_file_serve"),

    # documents CRUD
    path("users/<int:user_id>/documents/create/", views.document_create, name="document_create"),
    path("users/<int:user_id>/documents/<int:doc_id>/edit/", views.document_edit, name="document_edit"),
    path("users/<int:user_id>/documents/<int:doc_id>/delete/", views.document_delete, name="document_delete"),
    path("users/<int:user_id>/documents/<int:doc_id>/files/add/", views.document_files_add, name="document_files_add"),
    path("users/<int:user_id>/documents/<int:doc_id>/files/<int:file_id>/delete/", views.document_file_delete, name="document_file_delete"),
    path("users/<int:user_id>/documents/<int:doc_id>/files/<int:file_id>/view/", views.document_file_serve, name="document_file_serve"),
    path("users/<int:user_id>/documents/<int:doc_id>/view/", views.document_view, name="document_view"),



    # универсальная ручка просмотра папки
    path("users/<int:user_id>/docs/<str:kind>/", views.docs_list, name="docs_list"),
]
