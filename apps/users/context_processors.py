def notifications(request):
    if not request.user.is_authenticated:
        return {}

    unread_count = request.user.notifications.filter(is_read=False).count()

    return {
        'unread_count':  unread_count,
        'notifications': request.user.notifications.all()[:6],
    }