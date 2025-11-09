from django import forms

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
        if c["password"] != c["password2"]:
            raise forms.ValidationError("Пароли не совпадают")
        return c
