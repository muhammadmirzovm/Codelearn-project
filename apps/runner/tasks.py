"""
Celery tasks for background code evaluation.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evaluate_submission_task(self, submission_pk: int):
    """
    Celery task: evaluate a single submission against hidden test cases.
    Retries up to 2 times on failure.
    """
    from apps.runner.services import _evaluate_submission_sync
    try:
        _evaluate_submission_sync(submission_pk)
    except Exception as exc:
        logger.exception('Evaluation failed for submission %s', submission_pk)
        raise self.retry(exc=exc)
