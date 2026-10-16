import os
from pathlib import Path
import re
import shutil
import subprocess

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

OUTPUT_PATH = Path(__file__).resolve().parent / "baseline" / "current_as_is_schema.sql"
DEFAULT_URL = "mysql+pymysql://root:0000@localhost:3306/control_asistencias?charset=utf8mb4"


def main():
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    url = make_url(database_url)
    if url.drivername != "mysql+pymysql" or not url.database or not url.username:
        raise RuntimeError("DATABASE_URL must be a complete mysql+pymysql URL")

    mysqldump = shutil.which("mysqldump") or shutil.which("mariadb-dump")
    if not mysqldump:
        raise RuntimeError("mysqldump or mariadb-dump is required")

    command = [
        mysqldump,
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 3306}",
        f"--user={url.username}",
        "--single-transaction",
        "--quick",
        "--no-data",
        "--skip-comments",
        "--skip-triggers",
        "--default-character-set=utf8mb4",
        url.database,
    ]
    environment = os.environ.copy()
    if url.password:
        environment["MYSQL_PWD"] = url.password
    else:
        environment.pop("MYSQL_PWD", None)

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
    if result.returncode:
        raise RuntimeError(f"Schema dump failed: {result.stderr.strip()}")

    sql = result.stdout
    sql = re.sub(r"DEFINER=`[^`]*`@`[^`]*`", "DEFINER=CURRENT_USER", sql)
    if re.search(r"(?im)^\s*(?:CREATE\s+DATABASE|USE)\b", sql):
        raise RuntimeError("Refusing to save a dump containing database-selection directives")
    if re.search(r"(?im)^\s*INSERT\s+INTO\b", sql):
        raise RuntimeError("Refusing to save a schema baseline containing data")

    header = (
        "-- Current as-is schema baseline for isolated development and testing.\n"
        "-- Schema only: no table data, routines, events, triggers, or database-selection directives.\n"
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(header + sql, encoding="utf-8")
    print(f"Saved schema-only baseline to {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
