from __future__ import annotations

import ssl

from celery import Celery

from workforceiq import create_app


def make_celery() -> Celery:
    flask_app = create_app()
    celery_app = Celery(
        flask_app.import_name,
        broker=flask_app.config["CELERY_BROKER_URL"],
        backend=flask_app.config["CELERY_RESULT_BACKEND"],
    )
    config = {
        "imports": ("workforceiq.tasks",),
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
    }
    if flask_app.config["CELERY_BROKER_URL"].startswith("rediss://"):
        config["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    if flask_app.config["CELERY_RESULT_BACKEND"].startswith("rediss://"):
        config["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

    celery_app.conf.update(**config)

    class FlaskContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskContextTask
    return celery_app


celery = make_celery()
