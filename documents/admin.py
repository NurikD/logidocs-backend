from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from .models import Document

User = get_user_model()

class ChangeOwnerForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), label="Новый владелец")

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "type_badge", "version", "expires_at", "updated_at", "owner")
    list_filter = ("type", "expires_at", "owner")
    search_fields = ("title", "type", "owner__username", "owner__last_name", "owner__first_name")
    ordering = ("title",)
    list_per_page = 50

    fields = ("title", "type", "file", "version", "expires_at", "owner", "updated_at")
    readonly_fields = ("version", "updated_at")

    actions = ["bump_version", "change_owner_action"]

    @admin.display(description="Тип")
    def type_badge(self, obj: Document):
        color = "#2196F3"
        t = (obj.type or "").lower()
        if "лиценз" in t: color = "#4CAF50"
        elif "разреш" in t: color = "#2196F3"
        elif "полис" in t: color = "#FF9800"
        elif "сертифик" in t: color = "#7E57C2"
        return format_html('<span style="padding:2px 8px;border-radius:10px;background:{};color:#fff">{}</span>',
                           color, obj.type or "—")

    def save_model(self, request, obj, form, change):
        if change and "file" in form.changed_data:
            obj.version = (obj.version or 0) + 1
        super().save_model(request, obj, form, change)

    @admin.action(description="Увеличить версию (+1)")
    def bump_version(self, request, queryset):
        updated = 0
        for d in queryset:
            d.version = (d.version or 0) + 1
            d.save(update_fields=["version"])
            updated += 1
        self.message_user(request, f"Версия увеличена у {updated} документ(ов)")

    @admin.action(description="Сменить владельца…")
    def change_owner_action(self, request, queryset):
        # Экшен с формой (один шаг)
        if "apply" in request.POST:
            form = ChangeOwnerForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data["user"]
                count = queryset.update(owner=user)
                self.message_user(request, f"Назначено владельцем: {user} для {count} документ(ов)")
                return
        else:
            form = ChangeOwnerForm()

        return admin.helpers.render_to_response(
            request,
            "admin/change_owner.html",  # см. шаблон ниже (минимальный)
            context={
                "documents": queryset,
                "form": form,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )
