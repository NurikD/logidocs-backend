# adminui/forms.py
from django import forms
from django.contrib.auth import get_user_model
from accounts.models import Document

User = get_user_model()


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, label="Логин")
    first_name = forms.CharField(max_length=150, required=False, label="Имя")
    last_name  = forms.CharField(max_length=150, required=False, label="Фамилия")
    email      = forms.EmailField(required=False, label="Email")
    is_staff   = forms.BooleanField(initial=True, required=False, label="Доступ в админку")
    is_active  = forms.BooleanField(initial=True, required=False, label="Активен")


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "kind", "is_active", "expires_at"]
        widgets = {"expires_at": forms.DateInput(attrs={"type": "date"})}


# ======== многофайловый input ========

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned = []
        for d in data:
            cleaned.append(super().clean(d, initial))
        return cleaned


class DocumentFilesForm(forms.Form):
    files = MultipleFileField(required=False)
