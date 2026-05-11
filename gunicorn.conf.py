import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"


def _int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return max(minimum, int(raw))


# Keep production defaults conservative for small Docker hosts. Scale up with
# WEB_CONCURRENCY explicitly instead of relying on host CPU visibility.
workers = _int_env("WEB_CONCURRENCY", 2)
threads = _int_env("GUNICORN_THREADS", 2)
timeout = _int_env("GUNICORN_TIMEOUT", 60)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
