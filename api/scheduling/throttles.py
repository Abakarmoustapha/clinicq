import re

from rest_framework.throttling import SimpleRateThrottle


class BookingCodeThrottle(SimpleRateThrottle):
    """Limits how often one booking code can be checked, whoever asks.

    Patients in the same waiting room often share one internet connection,
    so a limit per connection alone would block all of them together.
    """

    scope = "queue_per_code"

    def get_cache_key(self, request, view):
        code = str(view.kwargs.get("code", "")).upper()
        code = re.sub(r"[^A-Z0-9]", "", code)[:20]
        return self.cache_format % {"scope": self.scope, "ident": code}


class QueueIpThrottle(SimpleRateThrottle):
    """A generous limit per connection, so nobody can try codes in bulk."""

    scope = "queue_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }