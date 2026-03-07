from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sessions_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='duration_minutes',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
