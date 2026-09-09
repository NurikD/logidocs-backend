from django.db import migrations


def convert_personal_to_business(apps, schema_editor):
    Document = apps.get_model("accounts", "Document")
    Document.objects.filter(kind="personal").update(kind="business")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_alter_document_kind_vehicle_document_vehicle_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_personal_to_business, noop),
    ]
