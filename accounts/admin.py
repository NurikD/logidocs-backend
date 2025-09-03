# backend/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string
from django.utils.html import format_html

from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # колонки в списке
    list_display = (
        "username", "full_name", "email", "is_active",
        "is_staff", "last_login", "must_change_pw_badge",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "must_change_pw", "date_joined")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    list_per_page = 50
    date_hierarchy = "date_joined"

    # поля в форме
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Персональные данные", {"fields": ("first_name", "last_name", "email")}),
        ("Доступ", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Безопасность", {"fields": ("must_change_pw",)}),
        ("Системные", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("last_login", "date_joined")

    # добавление пользователя — упрощённо
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "must_change_pw", "is_staff", "is_superuser"),
        }),
    )

    actions = ["force_password_reset", "generate_temp_password", "deactivate_users", "activate_users"]

    @admin.display(description="ФИО", ordering="last_name")
    def full_name(self, obj: User):
        fn = f"{obj.last_name} {obj.first_name}".strip()
        return fn or "—"

    @admin.display(description="Смена пароля", boolean=False)
    def must_change_pw_badge(self, obj: User):
        color = "#F44336" if obj.must_change_pw else "#4CAF50"
        text = "Обязательна" if obj.must_change_pw else "Нет"
        return format_html('<span style="padding:2px 8px;border-radius:10px;background:{};color:white">{}</span>', color, text)

    @admin.action(description="Принудить смену пароля")
    def force_password_reset(self, request, queryset):
        updated = queryset.update(must_change_pw=True)
        self.message_user(request, f"Помечено {updated} пользовател(я/ей) для принудительной смены пароля.")

    @admin.action(description="Сгенерировать временный пароль (и пометить к смене)")
    def generate_temp_password(self, request, queryset):
        # Генерим и показываем админу (без e-mail рассылки)
        msgs = []
        for u in queryset:
            temp = get_random_string(12)  # например: 'a8F...'
            u.set_password(temp)
            u.must_change_pw = True
            u.save(update_fields=["password", "must_change_pw"])
            msgs.append(f"{u.username}: {temp}")
        # Покажем в сообщении (не логируем в БД)
        self.message_user(request, "Сгенерированы пароли:\n" + "\n".join(msgs))

    @admin.action(description="Деактивировать пользователей")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано: {updated}")

    @admin.action(description="Активировать пользователей")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано: {updated}")


# по желанию — убираем группы из списка (если не используешь)
# admin.site.unregister(Group)
