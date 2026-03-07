"""
Student-facing submission views.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden

from .models import Submission


@login_required
def submission_detail(request, pk):
    """Show a single submission's results to its owner."""
    sub = get_object_or_404(Submission, pk=pk)
    if sub.student != request.user and not request.user.is_teacher:
        return HttpResponseForbidden()
    return render(request, 'submissions/submission_detail.html', {'submission': sub})
