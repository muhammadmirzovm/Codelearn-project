from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sessions_app', '0002_session_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='activated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
