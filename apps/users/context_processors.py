def notifications(request):
    if not request.user.is_authenticated:
        return {}
 
    unread_count = request.user.notifications.filter(is_read=False).count()
 
    open_tickets_count = 0
    if request.user.is_superuser:
        try:
            from apps.support.models import Ticket
            open_tickets_count = Ticket.objects.filter(status='open').count()
        except Exception:
            pass
 
    return {
        'unread_count':       unread_count,
        'notifications':      request.user.notifications.all()[:6],
        'open_tickets_count': open_tickets_count,
    }