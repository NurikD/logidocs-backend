# adminui/views.py
import secrets
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Document, DocumentFile, InviteToken, Vehicle, add_months  # твои модели
from .forms import UserCreateForm, DocumentForm, DocumentFilesForm

User = get_user_model()

INVITE_TTL = timedelta(days=3)


def _create_invite_link(request, user):
    InviteToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    invite = InviteToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + INVITE_TTL,
    )
    return request.build_absolute_uri(reverse("set_password", args=[invite.token]))

@staff_member_required
def users_list(request):
    q = request.GET.get("q","").strip().lower()

    qs = User.objects.only("id","username","first_name","last_name","phone","is_active","date_joined")

    if q:
        qs = (qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q)
              | qs.filter(last_name__icontains=q) | qs.filter(phone__icontains=q)
              | qs.filter(vehicles__plate__icontains=q)).distinct()

    # считаем ТОЛАЛЬНОЕ количество (до среза)
    users_total_count = qs.count()

    # теперь применяем срез только для отображения первых 9
    if not q:
        qs = qs.order_by("-date_joined")[:9]
    else:
        qs = qs.order_by("-date_joined")

    users = qs

    # если это вызов через HTMX — отдаём только grid
    if request.headers.get("HX-Request"):
        return render(request, "adminui/_users_grid.html", {"users": users})

    return render(
        request,
        "adminui/users_list.html",
        {
            "users": users,
            "q": q,
            "users_total_count": users_total_count,
        }
    )


@staff_member_required
@transaction.atomic
def user_create(request):
    if request.method == "POST":
        mode = request.POST.get("mode", "single")
        form = UserCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            if mode == "multi":
                username = cd.get("username", "").strip()
                plates = [p.strip() for p in request.POST.getlist("vehicle_plate") if p.strip()]
            else:
                username = request.POST.get("plate", "").strip()
                plates = []

            if not username:
                form.add_error(None, "Укажите логин" if mode == "multi" else "Укажите номер автомобиля")
            elif User.objects.filter(username=username).exists():
                form.add_error(None, "Логин уже существует")
            elif mode == "multi" and not plates:
                form.add_error(None, "Добавьте хотя бы один автомобиль")
            elif mode == "multi" and Vehicle.objects.filter(plate__in=plates).exists():
                form.add_error(None, "Один из номеров уже занят другим клиентом")
            else:
                u = User(
                    username=username,
                    first_name=cd.get("first_name",""),
                    last_name=cd.get("last_name",""),
                    phone=cd.get("phone",""),
                    is_staff=cd.get("is_staff", True),
                    is_active=cd.get("is_active", True),
                )
                u.set_unusable_password()
                u.save()

                for plate in plates:
                    Vehicle.objects.create(owner=u, plate=plate)

                link = _create_invite_link(request, u)
                messages.success(request, f"Пользователь создан. Отправьте клиенту ссылку для установки пароля (действует 3 дня):\n{link}")
                return redirect("adminui:user_detail", user_id=u.id)

    else:
        form = UserCreateForm()

    return render(request, "adminui/user_create.html", {"form": form})



@staff_member_required
def user_detail(request, user_id: int):
    user_obj = get_object_or_404(User, pk=user_id)

    vehicles = list(
        user_obj.vehicles.annotate(documents_count=Count("documents")).order_by("plate")
    )
    if vehicles:
        docs_no_vehicle_count = Document.objects.filter(owner=user_obj, vehicle__isnull=True).count()
        return render(request, "adminui/user_detail_vehicles.html", {
            "user_obj": user_obj,
            "vehicles": vehicles,
            "docs_no_vehicle_count": docs_no_vehicle_count,
        })

    qs = (Document.objects
          .filter(owner=user_obj, vehicle__isnull=True)
          .prefetch_related("files")
          .order_by("title"))

    docs_business = [d for d in qs if d.kind == Document.Kind.BUSINESS]
    docs_dozvol   = [d for d in qs if d.kind == Document.Kind.DOZVOL]

    return render(request, "adminui/user_detail.html", {
        "mode": "view",
        "user_obj": user_obj,

        "docs_business": docs_business,
        "docs_dozvol": docs_dozvol,

        "doc_form": DocumentForm(),
        "files_form": DocumentFilesForm(),
        # не надо choices в шаблоне теперь
    })


@staff_member_required
def vehicle_add(request, user_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        raise Http404
    plate = request.POST.get("plate", "").strip()
    if not plate:
        messages.error(request, "Укажите номер автомобиля")
    elif Vehicle.objects.filter(plate=plate).exists():
        messages.error(request, "Такой номер уже занят")
    else:
        Vehicle.objects.create(owner=user_obj, plate=plate)
        messages.success(request, "Автомобиль добавлен")
    return redirect("adminui:user_detail", user_id=user_id)


@staff_member_required
def vehicle_delete(request, user_id: int, vehicle_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    vehicle_obj = get_object_or_404(Vehicle, pk=vehicle_id, owner=user_obj)
    if request.method != "POST":
        raise Http404
    if vehicle_obj.documents.exists():
        messages.error(request, "В папке есть документы — сначала удалите их")
    else:
        vehicle_obj.delete()
        messages.success(request, "Автомобиль удалён")
    return redirect("adminui:user_detail", user_id=user_id)


@staff_member_required
def vehicle_detail(request, user_id: int, vehicle_id: int | None = None):
    user_obj = get_object_or_404(User, pk=user_id)
    vehicle_obj = get_object_or_404(Vehicle, pk=vehicle_id, owner=user_obj) if vehicle_id else None

    qs = (Document.objects
          .filter(owner=user_obj, vehicle=vehicle_obj)
          .prefetch_related("files")
          .order_by("title"))
    docs_business = [d for d in qs if d.kind == Document.Kind.BUSINESS]
    docs_dozvol   = [d for d in qs if d.kind == Document.Kind.DOZVOL]

    if vehicle_obj:
        business_url = reverse("adminui:vehicle_docs_list", args=[user_id, vehicle_obj.id, "business"])
        dozvol_url = reverse("adminui:vehicle_docs_list", args=[user_id, vehicle_obj.id, "dozvol"])
    else:
        business_url = reverse("adminui:docs_list", args=[user_id, "business"])
        dozvol_url = reverse("adminui:docs_list", args=[user_id, "dozvol"])

    return render(request, "adminui/vehicle_detail.html", {
        "user_obj": user_obj,
        "vehicle_obj": vehicle_obj,
        "docs_business": docs_business,
        "docs_dozvol": docs_dozvol,
        "business_url": business_url,
        "dozvol_url": dozvol_url,
    })



def _docs_by_kind(request, user_id:int, kind:str, title_ru:str, vehicle_id=None):
    user_obj = get_object_or_404(User, pk=user_id)
    vehicle_obj = get_object_or_404(Vehicle, pk=vehicle_id, owner=user_obj) if vehicle_id else None
    docs = list(Document.objects.filter(owner=user_obj, vehicle=vehicle_obj, kind=kind).order_by("-updated_at"))

    if request.method == "POST":
        # создание документа
        title = request.POST.get("title","").strip()
        files = request.FILES.getlist("files")

        error = None
        issued_at = None
        expires_at = None

        if not title:
            error = "Название обязательно"
        elif kind == Document.Kind.BUSINESS:
            issued_raw = request.POST.get("issued_at") or None
            if not issued_raw:
                error = "Укажите дату оформления"
            else:
                try:
                    issued_at = date.fromisoformat(issued_raw)
                except ValueError:
                    error = "Некорректная дата оформления"
                else:
                    expires_at = add_months(issued_at, 2)
        else:
            expires_at = request.POST.get("expires_at") or None

        if error:
            messages.error(request, error)
        else:
            with transaction.atomic():
                d = Document.objects.create(
                    owner=user_obj,
                    vehicle=vehicle_obj,
                    kind=kind,
                    title=title,
                    issued_at=issued_at,
                    expires_at=expires_at,
                )
                for f in files:
                    DocumentFile.objects.create(document=d, file=f)
            messages.success(request, "Документ создан")
            return redirect(request.path)

    for d in docs:
        if vehicle_obj:
            d.view_url = reverse("adminui:vehicle_document_view", args=[user_id, vehicle_obj.id, d.id])
        else:
            d.view_url = reverse("adminui:document_view", args=[user_id, d.id])

    if vehicle_obj:
        back_url = reverse("adminui:vehicle_detail", args=[user_id, vehicle_obj.id])
    elif Vehicle.objects.filter(owner_id=user_id).exists():
        back_url = reverse("adminui:vehicle_detail_unassigned", args=[user_id])
    else:
        back_url = reverse("adminui:user_detail", args=[user_id])

    return render(request,"adminui/docs_list.html",{
        "user_obj":user_obj,
        "vehicle_obj": vehicle_obj,
        "docs":docs,
        "title_ru":title_ru,
        "kind":kind,
        "back_url": back_url,
    })

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
    if kind not in ["business","dozvol"]:
        raise Http404

    map_ru = {
        "business": "Путевка",
        "dozvol":   "Дозвол",
    }

    return _docs_by_kind(request, user_id, kind, map_ru[kind])


@staff_member_required
def vehicle_docs_list(request, user_id:int, vehicle_id:int, kind:str):
    if kind not in ["business","dozvol"]:
        raise Http404

    map_ru = {
        "business": "Путевка",
        "dozvol":   "Дозвол",
    }

    return _docs_by_kind(request, user_id, kind, map_ru[kind], vehicle_id=vehicle_id)


@staff_member_required
def document_view(request, user_id, doc_id, vehicle_id=None):
    user_obj = get_object_or_404(User, id=user_id)
    vehicle_obj = get_object_or_404(Vehicle, pk=vehicle_id, owner=user_obj) if vehicle_id else None
    doc = get_object_or_404(Document, owner_id=user_id, vehicle=vehicle_obj, id=doc_id)

    # Добавляем информацию о типе файла
    files = []
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']

    for f in doc.files.all():
        if vehicle_obj:
            file_url = reverse("adminui:vehicle_document_file_serve", args=[user_id, vehicle_obj.id, doc.id, f.id])
        else:
            file_url = reverse("adminui:document_file_serve", args=[user_id, doc.id, f.id])
        files.append({
            'object': f,
            'is_image': any(f.file.name.lower().endswith(ext) for ext in image_extensions),
            'url': file_url,
        })

    if vehicle_obj:
        back_url = reverse("adminui:vehicle_docs_list", args=[user_id, vehicle_obj.id, doc.kind])
    else:
        back_url = reverse("adminui:docs_list", args=[user_id, doc.kind])

    return render(request, "adminui/document_view.html", {
        "user_obj": user_obj,
        "vehicle_obj": vehicle_obj,
        "document": doc,
        "files": files,
        "back_url": back_url,
    })


@staff_member_required
def password_reset_link(request, user_id: int):
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        raise Http404
    link = _create_invite_link(request, user_obj)
    messages.success(request, f"Ссылка для установки пароля (действует 3 дня):\n{link}")
    return redirect("adminui:user_detail", user_id=user_id)


@staff_member_required
def document_file_serve(request, user_id: int, doc_id: int, file_id: int, vehicle_id=None):
    user_obj = get_object_or_404(User, pk=user_id)
    doc = get_object_or_404(Document, pk=doc_id, owner=user_obj, vehicle_id=vehicle_id)
    file_obj = get_object_or_404(doc.files, pk=file_id)
    return FileResponse(
        file_obj.file.open("rb"),
        as_attachment=False,
        filename=file_obj.filename,
        content_type=file_obj.content_type,
    )
