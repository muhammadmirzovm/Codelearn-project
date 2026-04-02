from django.core.management.base import BaseCommand
from apps.users.models import GroupMembership
from apps.journals.models import Record


class Command(BaseCommand):
    help = 'Create missing records for all students'

    def handle(self, *args, **kwargs):
        count = 0
        for membership in GroupMembership.objects.all():
            try:
                lessons = membership.group.journal.lessons.filter(
                    date__gte=membership.joined_at
                )
                for lesson in lessons:
                    _, created = Record.objects.get_or_create(
                        lesson=lesson,
                        student=membership.student,
                        defaults={'grade': 0, 'attended': False}
                    )
                    if created:
                        count += 1
            except Exception as e:
                self.stdout.write(f'Error: {e}')
        self.stdout.write(self.style.SUCCESS(f'Created {count} missing records!'))