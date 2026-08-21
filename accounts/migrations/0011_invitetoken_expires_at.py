import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_invitetoken_used_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitetoken',
            name='expires_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
