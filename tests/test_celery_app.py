from __future__ import annotations

from workforceiq.celery_app import make_celery


def test_celery_app_uses_flask_runtime_config():
    celery = make_celery()

    assert celery.conf.broker_url
    assert celery.conf.result_backend
    assert celery.conf.task_serializer == "json"
