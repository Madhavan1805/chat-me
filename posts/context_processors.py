from .models import Message, Notification

def unread_messages_count(request):
    if request.user.is_authenticated:
        count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return {'unread_count': count}
    return {'unread_count': 0}

def unread_notifications_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(receiver=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
