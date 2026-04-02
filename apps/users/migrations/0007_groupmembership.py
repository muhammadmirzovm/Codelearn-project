from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def copy_and_drop(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(
            "INSERT INTO users_groupmembership (student_id, group_id, joined_at) "
            "SELECT user_id, group_id, CURRENT_DATE FROM users_group_students "
            "ON CONFLICT DO NOTHING"
        )
    else:
        schema_editor.execute(
            "INSERT OR IGNORE INTO users_groupmembership (student_id, group_id, joined_at) "
            "SELECT user_id, group_id, DATE('now') FROM users_group_students"
        )
    schema_editor.execute("DROP TABLE IF EXISTS users_group_students")


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_cointransaction'),
    ]

    operations = [
        # Step 1: Create GroupMembership table
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='users.group')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('student', 'group')},
            },
        ),

        # Step 2: Copy existing M2M data and drop old table
        migrations.RunPython(copy_and_drop, reverse_code=migrations.RunPython.noop),

        # Step 3: Update Django state only — no DB changes
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='group',
                    name='students',
                    field=models.ManyToManyField(
                        blank=True,
                        limit_choices_to={'role': 'student'},
                        related_name='student_groups',
                        through='users.GroupMembership',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]