from django.utils import timezone


class UpdateLastSeenMiddleware:
    """Update profile.last_seen on each authenticated request (throttled to ~60s)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and hasattr(user, "profile"):
            profile = user.profile
            now = timezone.now()
            # Avoid writing on every single request
            if profile.last_seen is None or (now - profile.last_seen).total_seconds() > 60:
                type(profile).objects.filter(pk=profile.pk).update(last_seen=now)
        return response
