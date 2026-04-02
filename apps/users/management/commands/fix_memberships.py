from django.core.management.base import BaseCommand
from apps.users.models import GroupMembership


class Command(BaseCommand):
    help = 'Fix joined_at dates for existing memberships'

    def handle(self, *args, **kwargs):
        count = 0
        for membership in GroupMembership.objects.all():
            try:
                earliest_lesson = membership.group.journal.lessons.order_by('date').first()
                if earliest_lesson:
                    GroupMembership.objects.filter(pk=membership.pk).update(joined_at=earliest_lesson.date)
                else:
                    GroupMembership.objects.filter(pk=membership.pk).update(joined_at=membership.group.created_at.date())
            except Exception:
                GroupMembership.objects.filter(pk=membership.pk).update(joined_at=membership.group.created_at.date())
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Fixed {count} memberships!'))