from sqlalchemy.engine import make_url

SAFE_TEST_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}


def assert_safe_test_database_url(database_url):
    url = make_url(database_url)
    if url.drivername != "mysql+pymysql":
        raise RuntimeError("Tests require a mysql+pymysql database URL")
    if url.host not in SAFE_TEST_HOSTS:
        raise RuntimeError("Tests can only use the Docker db service or a loopback database host")
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError("Tests require a database name ending in _test")
    return url
