"""Progressive enhancement for save forms.

Forms marked `data-ajax` are sent with fetch() and `X-Requested-With: XMLHttpRequest`.
`ajax_json` wraps an ordinary view: without that header the view behaves exactly as before
(redirect + flash message). With it, the redirect/render is turned into JSON:

    {"ok": bool, "messages": [{"level": "success"|"error"|..., "text": "..."}], "redirect": "/sell/"}

The browser then refreshes only the `[data-live]` regions of the current page. CSRF, login and
permission checks are untouched because the wrapped view (and its decorators) still run.
"""

from functools import wraps

from django.contrib import messages
from django.http import JsonResponse


def is_ajax(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def ajax_json(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        if not is_ajax(request) or request.method != "POST":
            return response
        if response.status_code >= 400 and response.status_code != 404:
            return response
        msgs = [{"level": m.level_tag or "info", "text": str(m)} for m in messages.get_messages(request)]
        if response.status_code == 404:
            return JsonResponse({"ok": False, "messages": [{"level": "error", "text": "Not found."}]}, status=404)
        ok = not any(m["level"] == "error" for m in msgs)
        data = {"ok": ok, "messages": msgs}
        if response.status_code in (301, 302, 303):
            data["redirect"] = response["Location"]
        return JsonResponse(data, status=200 if ok else 400)

    return wrapper
