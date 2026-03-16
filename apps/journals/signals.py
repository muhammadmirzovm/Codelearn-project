from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.users.models import Group          # ← fix here too
from apps.journals.models import Journal


@receiver(post_save, sender=Group)
def create_journal_for_group(sender, instance, created, **kwargs):
    if created:
        Journal.objects.create(group=instance)