import os

from dev.database import DEVELOPMENT_DATABASE, reset_database


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    reset_database(database_url, allowed_databases=(DEVELOPMENT_DATABASE,))

    from app import app
    from dev.enhance_academic_year import apply_schema, backfill
    from dev.synthetic_data import seed_synthetic_data

    with app.app_context():
        apply_schema()
        counts = seed_synthetic_data()
        backfill()
    print("Development database reset, enhanced, and seeded: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
