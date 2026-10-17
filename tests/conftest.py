import os

import pytest

DEFAULT_TEST_URL = "mysql+pymysql://asistencias_dev:dev_user_only@127.0.0.1:3307/control_asistencias_test?charset=utf8mb4"

compose_url = os.environ.get("DATABASE_URL") if os.environ.get("APP_ENV") == "testing" else None
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or compose_url or DEFAULT_TEST_URL
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_only_secret"
os.environ["ENABLE_ACADEMIC_PERIOD_ADMIN"] = "1"


@pytest.fixture(scope="session")
def app():
    from dev.database import TEST_DATABASE, reset_database

    reset_database(os.environ["DATABASE_URL"], allowed_databases=(TEST_DATABASE,))

    from app import app as flask_app
    from dev.enhance_academic_year import apply_schema, backfill
    from dev.synthetic_data import seed_synthetic_data

    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        apply_schema()
        seed_synthetic_data()
        backfill()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def rollback_database_changes(app):
    from models import db

    with app.app_context():
        yield
        db.session.rollback()
        db.session.remove()
