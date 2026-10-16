from pathlib import Path

import pymysql
from pymysql.constants import CLIENT
from sqlalchemy.engine import make_url

BASELINE_SCHEMA = Path(__file__).resolve().parent / "baseline" / "current_as_is_schema.sql"
LOCAL_DATABASE_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}
DEVELOPMENT_DATABASE = "control_asistencias_dev"
TEST_DATABASE = "control_asistencias_test"


def database_settings(database_url, allowed_databases):
    url = make_url(database_url)
    if url.drivername != "mysql+pymysql":
        raise RuntimeError("Development tools require a mysql+pymysql database URL")
    if url.host not in LOCAL_DATABASE_HOSTS:
        raise RuntimeError("Development tools can only modify a local Docker or loopback database")
    if url.database not in set(allowed_databases):
        raise RuntimeError(f"Refusing to modify unexpected database: {url.database}")
    if not url.username:
        raise RuntimeError("Development database URL must include a username")
    return url


def reset_database(database_url, allowed_databases=(DEVELOPMENT_DATABASE, TEST_DATABASE), schema_path=BASELINE_SCHEMA):
    url = database_settings(database_url, allowed_databases)
    schema_path = Path(schema_path)
    if not schema_path.is_file():
        raise RuntimeError(f"Baseline schema not found: {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")
    connection = pymysql.connect(
        host=url.host,
        port=url.port or 3306,
        user=url.username,
        password=url.password or "",
        charset="utf8mb4",
        autocommit=True,
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{url.database}`")
            cursor.execute(
                f"CREATE DATABASE `{url.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.select_db(url.database)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            while cursor.nextset():
                pass
    finally:
        connection.close()
