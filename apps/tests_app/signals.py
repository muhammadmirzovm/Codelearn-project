from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GlobalTestAttempt
from apps.users.models import CoinTransaction


@receiver(post_save, sender=GlobalTestAttempt)
def award_coins_on_perfect_score(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.status != GlobalTestAttempt.STATUS_FINISHED:
        return
    if instance.score != instance.total or instance.total == 0:
        return
    if instance.test_pack.coin_reward <= 0:
        return

    already_rewarded = GlobalTestAttempt.objects.filter(
        test_pack=instance.test_pack,
        student=instance.student,
        coins_awarded=True,
    ).exclude(pk=instance.pk).exists()

    if already_rewarded:
        return

    CoinTransaction.objects.create(
        user=instance.student,
        amount=instance.test_pack.coin_reward,
        tx_type=CoinTransaction.TYPE_EARN,
        note=f'Global test 100%: {instance.test_pack.title}',
    )
    GlobalTestAttempt.objects.filter(pk=instance.pk).update(coins_awarded=True)
