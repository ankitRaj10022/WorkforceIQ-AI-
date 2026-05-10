from __future__ import annotations

from celery import Celery

from workforceiq import create_app


def make_celery() -> Celery:
    flask_app = create_app()
    celery_app = Celery(
        flask_app.import_name,
        broker=flask_app.config["CELERY_BROKER_URL"],
        backend=flask_app.config["CELERY_RESULT_BACKEND"],
    )
    celery_app.conf.update(
        imports=("workforceiq.tasks",),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    class FlaskContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskContextTask
    return celery_app


celery = make_celery()
