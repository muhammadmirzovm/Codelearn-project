import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='invite_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
