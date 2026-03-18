from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

from .models import Ticket
from apps.users.models import Notification


# ── User: submit contact form ─────────────────────────────────────────────
@login_required
def contact(request):
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        message  = request.POST.get('message', '').strip()
        category = request.POST.get('category', 'question')

        if not title or not message:
            messages.error(request, '❌ Title and message are required.')
            return render(request, 'support/contact.html', {
                'categories': Ticket.CATEGORY_CHOICES,
                'post': request.POST,
            })

        Ticket.objects.create(
            sender=request.user,
            title=title,
            message=message,
            category=category,
        )

        # Notify the user their ticket was received
        Notification.objects.create(
            recipient=request.user,
            title='✅ Support ticket received',
            message=f'Your message "{title}" has been received. We\'ll get back to you soon.',
            notif_type='success',
        )

        messages.success(request, '✅ Your message has been sent! We will reply soon.')
        return redirect('support:contact')

    return render(request, 'support/contact.html', {
        'categories': Ticket.CATEGORY_CHOICES,
    })


# ── User: view own tickets ────────────────────────────────────────────────
@login_required
def my_tickets(request):
    tickets = Ticket.objects.filter(sender=request.user)
    return render(request, 'support/my_tickets.html', {'tickets': tickets})


# ── Superuser: inbox ──────────────────────────────────────────────────────
def superuser_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


@superuser_required
def inbox(request):
    status   = request.GET.get('status', '')
    category = request.GET.get('category', '')

    tickets = Ticket.objects.select_related('sender').all()
    if status:
        tickets = tickets.filter(status=status)
    if category:
        tickets = tickets.filter(category=category)

    counts = {
        'open':        Ticket.objects.filter(status='open').count(),
        'in_progress': Ticket.objects.filter(status='in_progress').count(),
        'closed':      Ticket.objects.filter(status='closed').count(),
    }

    return render(request, 'support/inbox.html', {
        'tickets':    tickets,
        'counts':     counts,
        'categories': Ticket.CATEGORY_CHOICES,
        'statuses':   Ticket.STATUS_CHOICES,
        'filter_status':   status,
        'filter_category': category,
    })


@superuser_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'reply':
            reply  = request.POST.get('reply', '').strip()
            status = request.POST.get('status', ticket.status)
            if reply:
                ticket.reply  = reply
                ticket.status = status
                ticket.save(update_fields=['reply', 'status', 'updated_at'])

                # Notify the user
                Notification.objects.create(
                    recipient=ticket.sender,
                    title=f'💬 Reply to your ticket: {ticket.title}',
                    message=reply[:200],
                    notif_type='info',
                )
                messages.success(request, '✅ Reply sent and user notified.')
            else:
                messages.error(request, '❌ Reply cannot be empty.')

        elif action == 'status':
            new_status = request.POST.get('status')
            if new_status in dict(Ticket.STATUS_CHOICES):
                ticket.status = new_status
                ticket.save(update_fields=['status', 'updated_at'])
                messages.success(request, f'Status updated to {ticket.get_status_display()}')

        return redirect('support:ticket_detail', pk=pk)

    return render(request, 'support/ticket_detail.html', {
        'ticket':   ticket,
        'statuses': Ticket.STATUS_CHOICES,
    })