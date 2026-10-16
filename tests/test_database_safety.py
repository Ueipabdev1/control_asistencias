import pytest

from utils.database_safety import assert_safe_test_database_url


@pytest.mark.parametrize("host", ["db", "localhost", "127.0.0.1", "[::1]"])
def test_accepts_local_test_databases(host):
    url = f"mysql+pymysql://user:password@{host}:3306/control_asistencias_test?charset=utf8mb4"
    assert assert_safe_test_database_url(url).database == "control_asistencias_test"


@pytest.mark.parametrize(
    "url",
    [
        "mysql+pymysql://user:password@db:3306/control_asistencias_dev",
        "mysql+pymysql://user:password@db:3306/control_asistencias",
        "mysql+pymysql://user:password@production.example:3306/control_asistencias_test",
        "mysql://user:password@db:3306/control_asistencias_test",
        "sqlite:///control_asistencias_test.db",
    ],
)
def test_rejects_unsafe_test_databases(url):
    with pytest.raises(RuntimeError):
        assert_safe_test_database_url(url)
