# backend/documents/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "type_badge", "version", "expires_at", "status_badge")
    list_filter = ("type", "expires_at")
    search_fields = ("title", "type")
    ordering = ("title",)
    list_per_page = 50
    date_hierarchy = "expires_at"
    actions = ["mark_expired", "bump_version"]

    fields = ("title", "type", "version", "expires_at")
    # readonly_fields = ()  # если надо что-то запретить редактировать

    @admin.display(description="Тип")
    def type_badge(self, obj: Document):
        color = "#2196F3"
        if obj.type:
            t = obj.type.lower()
            if "лиценз" in t:
                color = "#4CAF50"
            elif "разреш" in t:
                color = "#2196F3"
            elif "полис" in t:
                color = "#FF9800"
            elif "сертифик" in t:
                color = "#7E57C2"
        text = obj.type or "—"
        return format_html('<span style="padding:2px 8px;border-radius:10px;background:{};color:white">{}</span>', color, text)

    @admin.display(description="Статус")
    def status_badge(self, obj: Document):
        if obj.expires_at is None:
            return "—"
        from datetime import date, timedelta
        today = date.today()
        warn = obj.expires_at <= today + timedelta(days=30) and obj.expires_at >= today
        expired = obj.expires_at < today
        color = "#4CAF50"
        text = "Действует"
        if warn:
            color, text = "#FF9800", "Истекает"
        if expired:
            color, text = "#F44336", "Истёк"
        return format_html('<span style="padding:2px 8px;border-radius:10px;background:{};color:white">{}</span>', color, text)

    @admin.action(description="Пометить как истекшие (сегодня)")
    def mark_expired(self, request, queryset):
        from datetime import date
        updated = queryset.update(expires_at=date.today())
        self.message_user(request, f"Обновлено: {updated}")

    @admin.action(description="Увеличить версию (+1)")
    def bump_version(self, request, queryset):
        updated = 0
        for d in queryset:
            d.version = (d.version or 0) + 1
            d.save(update_fields=["version"])
            updated += 1
        self.message_user(request, f"Версия увеличена у {updated} документ(ов)")
