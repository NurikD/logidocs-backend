# adminui/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string

from accounts.models import Document, DocumentFile  # твои модели
from .forms import UserCreateForm, DocumentForm, DocumentFilesForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth import login

User = get_user_model()

@staff_member_required
def users_list(request):
    q = request.GET.get("q","").strip().lower()

    qs = User.objects.only("id","username","first_name","last_name","email","is_active","date_joined")

    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q) | qs.filter(email__icontains=q)
        users = qs.order_by("-date_joined")
    else:
        users = qs.order_by("-date_joined")[:6]

    # если это вызов через HTMX — отдаём только grid
    if request.headers.get("HX-Request"):
        return render(request, "adminui/_users_grid.html", {"users": users})

    return render(request, "adminui/users_list.html", {"users": users, "q": q})

@staff_member_required
@transaction.atomic
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            if User.objects.filter(username=cd["username"]).exists():
                form.add_error("username", "Логин уже существует")
            else:
                temp = get_random_string(12)
                u = User(
                    username=cd["username"],
                    first_name=cd.get("first_name",""),
                    last_name=cd.get("last_name",""),
                    email=cd.get("email",""),
                    is_staff=cd.get("is_staff", True),
                    is_active=cd.get("is_active", True),
                )
                if hasattr(u, "must_change_pw"):
                    u.must_change_pw = True
                u.set_password(temp)
                u.save()

                messages.success(request, f"Пользователь создан. Временный пароль:\n\n{u.username}: {temp}")
                return redirect("adminui:user_detail", user_id=u.id)

    else:
        form = UserCreateForm()

    return render(request, "adminui/user_create.html", {"form": form})



@staff_member_required
def user_detail(request, user_id: int):
    user_obj = get_object_or_404(User, pk=user_id)

    qs = (Document.objects
          .filter(owner=user_obj)
          .prefetch_related("files")
          .order_by("title"))

    docs_personal = [d for d in qs if d.kind == Document.Kind.PERSONAL]
    docs_business = [d for d in qs if d.kind == Document.Kind.BUSINESS]
    docs_dozvol   = [d for d in qs if d.kind == Document.Kind.DOZVOL]

    return render(request, "adminui/user_detail.html", {
        "mode": "view",
        "user_obj": user_obj,

        "docs_personal": docs_personal,
        "docs_business": docs_business,
        "docs_dozvol": docs_dozvol,

        "doc_form": DocumentForm(),
        "files_form": DocumentFilesForm(),
        # не надо choices в шаблоне теперь
    })



def _docs_by_kind(request, user_id:int, kind:str, title_ru:str):
    user_obj = get_object_or_404(User, pk=user_id)
    docs = Document.objects.filter(owner=user_obj, kind=kind).order_by("-updated_at")

    if request.method == "POST":
        # создание документа
        title = request.POST.get("title","").strip()
        expires_at = request.POST.get("expires_at") or None
        files = request.FILES.getlist("files")

        if not title:
            messages.error(request, "Название обязательно")
        else:
            with transaction.atomic():
                d = Document.objects.create(
                    owner=user_obj,
                    kind=kind,
                    title=title,
                    expires_at=expires_at
                )
                for f in files:
                    DocumentFile.objects.create(document=d, file=f)
            messages.success(request, "Документ создан")
            return redirect(request.path)

    return render(request,"adminui/docs_list.html",{
        "user_obj":user_obj,
        "docs":docs,
        "title_ru":title_ru,
        "kind":kind,
    })


@staff_member_required
def docs_by_kind_personal(request, user_id:int):
    return _docs_by_kind(request,user_id,"personal","Личные документы")


@staff_member_required
def docs_by_kind_business(request, user_id:int):
    return _docs_by_kind(request,user_id,"business","Разрешения / лицензии")


@staff_member_required
def docs_by_kind_dozvol(request, user_id:int):
    return _docs_by_kind(request,user_id,"dozvol","Дозвол")

@staff_member_required
@transaction.atomic
def document_create(request, user_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        raise Http404
    form = DocumentForm(request.POST)
    files_form = DocumentFilesForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.owner = user_obj
        doc.save()
        if files_form.is_valid():
            for f in files_form.cleaned_data.get("files") or []:
                DocumentFile.objects.create(document=doc, file=f)
        messages.success(request, "Документ создан")
    else:
        messages.error(request, "Исправьте ошибки формы документа")
    return redirect("adminui:user_detail", user_id=user_id)

@staff_member_required
@transaction.atomic
def document_edit(request, user_id: int, doc_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    doc = get_object_or_404(Document.objects.select_related("owner"), pk=doc_id, owner=user_obj)
    if request.method != "POST":
        raise Http404
    form = DocumentForm(request.POST, instance=doc)
    if form.is_valid():
        form.save()
        messages.success(request, "Документ обновлён")
    else:
        messages.error(request, "Исправьте ошибки формы")
    return redirect("adminui:user_detail", user_id=user_id)

@staff_member_required
@transaction.atomic
def document_delete(request, user_id: int, doc_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    doc = get_object_or_404(Document.objects.select_related("owner"), pk=doc_id, owner=user_obj)
    if request.method != "POST":
        raise Http404
    doc.delete()  # каскадно удалит DocumentFile
    messages.success(request, "Документ удалён")
    return redirect("adminui:user_detail", user_id=user_id)

@staff_member_required
@transaction.atomic
def document_files_add(request, user_id: int, doc_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    doc = get_object_or_404(Document.objects.select_related("owner").prefetch_related("files"), pk=doc_id, owner=user_obj)
    if request.method != "POST":
        raise Http404
    form = DocumentFilesForm(request.POST, request.FILES)
    if form.is_valid():
        for f in form.cleaned_data.get("files") or []:
            DocumentFile.objects.create(document=doc, file=f)
        messages.success(request, "Файлы добавлены")
    else:
        messages.error(request, "Выберите файлы")
    return redirect("adminui:user_detail", user_id=user_id)

@staff_member_required
@transaction.atomic
def document_file_delete(request, user_id: int, doc_id: int, file_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    doc = get_object_or_404(Document.objects.select_related("owner"), pk=doc_id, owner=user_obj)
    file_obj = get_object_or_404(doc.files, pk=file_id)
    if request.method != "POST":
        raise Http404
    file_obj.delete()
    messages.success(request, "Файл удалён")
    return redirect("adminui:user_detail", user_id=user_id)


@staff_member_required
def docs_list(request, user_id:int, kind:str):
    if kind not in ["personal","business","dozvol"]:
        raise Http404

    map_ru = {
        "personal": "Личные документы",
        "business": "Разрешения / лицензии",
        "dozvol":   "Дозвол",
    }

    return _docs_by_kind(request, user_id, kind, map_ru[kind])

@staff_member_required
def document_view(request, user_id, doc_id):
    user_obj = get_object_or_404(User, id=user_id)
    doc = get_object_or_404(Document, owner_id=user_id, id=doc_id)

    # Добавляем информацию о типе файла
    files = []
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']

    for f in doc.files.all():
        file_data = {
            'object': f,
            'is_image': any(f.file.name.lower().endswith(ext) for ext in image_extensions)
        }
        files.append(file_data)

    return render(request, "adminui/document_view.html", {
        "user_obj": user_obj,
        "document": doc,
        "files": files,
    })

