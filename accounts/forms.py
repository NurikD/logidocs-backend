from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class SetPasswordFormWithoutOldPassword(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password"
        }),
        label="Новый пароль"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password"
        }),
        label="Повторите пароль"
    )

    def clean(self):
        c = super().clean()
        password = c.get("password")
        if password and c.get("password2") and password != c["password2"]:
            raise forms.ValidationError("Пароли не совпадают")
        if password:
            if len(password) < 10:
                self.add_error("password", "Пароль слишком короткий (>=10).")
            else:
                try:
                    validate_password(password)
                except ValidationError as e:
                    self.add_error("password", e)
        return c


class RussianAdminAuthenticationForm(AdminAuthenticationForm):
    """Вход в /admin/ у нас читают клиенты и диспетчер, а не разработчики —
    подписи полей должны быть на русском, как везде в adminui."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Логин"
        self.fields["password"].label = "Пароль"
