from django.db import migrations


def revoke_client_staff(apps, schema_editor):
    """Клиенты создавались с is_staff=True — это открывало им весь /admin-ui/
    с документами других клиентов. Снимаем флаг со всех, кроме суперюзеров."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=False, is_staff=True).update(is_staff=False)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_document_issued_at_document_last_notified_date_and_more'),
    ]

    operations = [
        migrations.RunPython(revoke_client_staff, noop),
    ]
