"""A small fixed-window rate limiter for credential endpoints.

Backed by the Django cache, so it inherits whatever cache is configured. With
the default locmem cache the counters are per-process, which is enough to blunt
casual password guessing in development; point ``CACHES`` at Redis or Memcached
and the same code limits across every worker.
"""

import hashlib

from django.core.cache import cache


def client_ip(request):
    """Best-effort client address.

    ``X-Forwarded-For`` is only consulted for its first entry and is trusted
    only as far as the deployment's proxy makes it trustworthy.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key(scope, identifier):
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:32]
    return f"throttle:{scope}:{digest}"


def is_rate_limited(scope, identifier, *, limit, window_seconds):
    """Return True when ``identifier`` has already used up its allowance."""
    key = _key(scope, identifier)
    attempts = cache.get(key, 0)
    return attempts >= limit


def register_attempt(scope, identifier, *, window_seconds):
    """Count one attempt against ``identifier``."""
    key = _key(scope, identifier)
    try:
        # add() only succeeds when the key is absent, which is what starts the
        # window. incr() then extends the count without resetting the expiry.
        if cache.add(key, 1, window_seconds):
            return 1
        return cache.incr(key)
    except ValueError:
        # The key expired between add() and incr(); start a fresh window.
        cache.set(key, 1, window_seconds)
        return 1


def clear_attempts(scope, identifier):
    """Forget the counter, called after a successful authentication."""
    cache.delete(_key(scope, identifier))
