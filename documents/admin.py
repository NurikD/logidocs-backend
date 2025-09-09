from django.contrib import admin
from django.utils.html import format_html
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "type_badge", "version", "expires_at", "updated_at")
    list_filter = ("type", "expires_at")
    search_fields = ("title", "type")
    ordering = ("title",)
    list_per_page = 50
    fields = ("title", "type", "file", "version", "expires_at", "updated_at")
    readonly_fields = ("version", "updated_at")

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

    # Хук: если админ меняет файл из формы — увеличиваем версию
    def save_model(self, request, obj, form, change):
        if change and "file" in form.changed_data:
            obj.version = (obj.version or 0) + 1
        super().save_model(request, obj, form, change)
