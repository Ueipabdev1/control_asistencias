# Isolated development and migration testing

This environment is for developing and rehearsing database enhancements without changing production. It uses MariaDB 11.8 and Python 3.11, matching the current database server major/minor version and `runtime.txt`.

## Environments

- `control_asistencias_dev`: persistent development database for manual checks and optional migration rehearsal.
- `control_asistencias_test`: disposable database reset and seeded for every automated test run.
- Application: `http://127.0.0.1:5017`.
- Development database: loopback port `3307`; the existing local MariaDB on `3306` is not reused.

Compose explicitly sets development database URLs. It does not use the production `DATABASE_URL` from the project's `.env`.

## Quick start

Requirements: Docker with Compose v2.

```bash
bash dev/scripts/bootstrap.sh
```

The script builds the application image, starts MariaDB, recreates and seeds the development database, runs the automated tests, and starts the app.

Synthetic login only:

```text
admin@dev.test / dev-only
```

Run the tests again:

```bash
bash dev/scripts/test.sh
```

Reset the development database to the as-is schema plus synthetic data:

```bash
bash dev/scripts/reset_dev.sh
```

Useful commands:

```bash
docker compose -f compose.dev.yaml ps
docker compose -f compose.dev.yaml logs -f app db
docker compose -f compose.dev.yaml down
```

`docker compose -f compose.dev.yaml down -v` also deletes the development Docker volume. It does not affect production, but it permanently deletes local development/rehearsal data.

## Baseline and synthetic data

`dev/baseline/current_as_is_schema.sql` is a schema-only capture of the current database structure. It contains no table data and no `CREATE DATABASE` or `USE` directives.

To refresh that baseline with a read-only schema dump:

```bash
venv/bin/python -m dev.capture_current_schema
```

The synthetic seed creates 14 grades, 15 sections, 30 fictional students, 90 attendance rows, observations, teacher assignments, and legacy counterparts required by existing routes. It refuses to seed a non-empty database.

## Automated-test safety

- `pytest.ini` collects only `tests/`; the older root-level live-database scripts are not collected.
- Pytest resets only `control_asistencias_test` and applies the as-is schema before importing the app.
- When `APP_ENV=testing`, `app.py` rejects any URL whose host is not the Compose `db` service or loopback, or whose database name does not end in `_test`.
- The characterization test documents the existing attendance-attribution behavior. The academic-year enhancement should replace it with regression tests proving that historical attribution remains fixed after promotion and graduation.

## Optional production-copy rehearsal

A real full-data rehearsal has **not** been performed yet. When separately authorized:

1. Create a current production dump through the normal backup process. Use a dump without `CREATE DATABASE` or `USE` directives.
2. Store it under `dev/backups/`, which is Git-ignored. Do not commit production data.
3. Restore it only into the development container:

   ```bash
   bash dev/scripts/restore_dev_dump.sh dev/backups/current.sql
   ```

   The script requires confirmation and recreates only `control_asistencias_dev`.

4. Capture pre-migration row counts and attendance/report aggregates.
5. Apply the candidate migration only in the development container, run the application checks, and compare all post-migration aggregates with the baseline.
6. Reset or restore again to repeat the rehearsal. Do not point these commands at production and do not commit generated dumps or reports (`dev/reports/` is also Git-ignored).

## Minimal migration packet

`dev/migration_packet.py` defines the lean input contract for a rollover: `students.csv`, `sections.csv`, `teacher_sections.csv`, and `manifest.json`. It rejects unexpected columns, duplicate identities, unresolved sections, shared teacher emails, and invalid file hashes. Teacher emails can also be checked against exactly one active local professor.

Generate and validate the synthetic 2026-2027 packet:

```bash
venv/bin/python -m dev.build_synthetic_packet
```

The generated files live in `dev/packets/synthetic_2026_2027/` and contain only fictional identities. The packet has 30 students (28 continuing and 2 graduates), 15 sections, and 15 teacher-section assignments. Single-section grades use `A`; only 4to año has A/B. Real future extracts must use the same minimal fields and manifest version metadata.

## Read-only real draft extraction

Run the authorized minimal extraction with the system Python used by the existing Odoo/Google read-only wrappers:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m dev.extract_real_rollover_packet
```

The extractor uses a read-only application-database transaction, Odoo `fields_get`/`search_read`, the read-only Academic Team roster scope, offline Akdemia exports, and the latest cached Kampus publication. It has no rollover-apply path.

Real artifacts are written only to the Git-ignored `dev/backups/real_2026_2027/` directory with owner-only permissions. Row-level reconciliation stays there; `dev/reports/real_2026_2027_extraction.json` contains aggregate counts only. Never move these files into `dev/packets/` or commit them.

The 2026-10-17 draft is structurally valid but not migration-ready: 224 current students (213 continuing and 11 graduates), 47 student rows requiring review, 15 sections, and 86 teacher assignments across 23 matched profiles. The Odoo enrollment-journey authority rule validates 183 students directly and converts only secondary Akdemia/Excel disagreements into warnings when identity, journey state, name, graduation status, and target grade agree. Thirty Kampus teacher-group pairs remain blocked because their emails do not match an active local professor. Review the secure reconciliation and obtain a strict-ready packet before attempting a full production-copy rehearsal.

## Academic-year validation site

The enhanced synthetic validation environment can be rebuilt at:

```text
https://dev.ueipab.edu.ve/control_asistencias_enhance/
```

Synthetic login after a synthetic reset: `admin@dev.test` / `dev-only`. The site uses Gunicorn on loopback port 5018 and the isolated `control_asistencias_dev` database. It is separate from the existing `/control_asistencias/` service on port 5006. **The app and validation services are currently stopped because the database contains the authorized real-copy Window A rehearsal; do not expose that copy through the public URL.**

After the real-copy evidence is no longer needed, rebuild the enhanced development database to the synthetic 2025-2026 baseline and restart the isolated services. This permanently replaces the current development database:

```bash
docker compose -f compose.dev.yaml stop app validation
bash dev/scripts/reset_dev.sh
docker compose -f compose.dev.yaml up -d app validation
```

Open `/admin/periodos` to review and activate the synthetic 2026-2027 packet through the browser. For the CLI alternative, run `docker compose -f compose.dev.yaml run --rm --no-deps app python -m dev.apply_migration_packet` after the reset and before starting the services.

The admin validation page is `/admin/validacion-matricula`. The academic-structure management page is `/admin/estructura`, with grade and current-year section creation/editing, duplicate protection, no deletes, and no historical rewrites. Deactivation is blocked for sections with active enrollments, and used grade/section names are protected. Admins can open it from **Estructura académica** in the main sidebar; the entry is hidden from professors.

The academic-period manager is `/admin/periodos`, linked as **Períodos académicos** in the admin sidebar. It lists historical/current/planned periods, creates only non-current successor periods, reviews the bundled packet and database preflight, and performs the confirmed close-and-activate rollover. Mutations require `ENABLE_ACADEMIC_PERIOD_ADMIN=1`, an isolated dev/test database, a session-bound CSRF token, the reviewed packet fingerprint, and typed target-period confirmation. There is no direct `es_actual` editor or arbitrary packet-path input.

Previous end-to-end rollover verification activated 2026-2027 from 2025-2026 with 28 promotions, 2 graduates, and all 90 attendance links preserved. The combined suite now has 95 passing tests, including authorization, inactive sessions, assigned-section enforcement, planned-period attendance rejection, retired-enrollment historical reporting, and Window A migration guards.

## Window A runner and rehearsals

`window_a_migration.py` is the dedicated schema/backfill runner for Window A; `WINDOW_A_PRODUCTION_RUNBOOK.md` defines its authorization, backup, recovery, and deployment gates. It defaults to read-only preflight and is separate from the rollover-packet runner. Do not use it for Window B.

The synthetic MariaDB rehearsal passed legacy preflight, apply, independent verification, complete-state no-op, forced partial-DDL detection, recovery reset, reapplication, and HTTP smoke checks. It preserved all 30 fictional students and 90 attendance rows, kept 2025-2026 current, and created no target-year sections or enrollments.

The authorized real production-copy rehearsal then passed with 227 students, 39,009 attendance rows, 1,253 observations, 84 teacher assignments, 15 original tables, and 2 views preserved. All 7,873 historical attendance aggregate groups and 18 roster groups matched. Forced-failure recovery, no-op rerun, and authenticated HTTP checks also passed; historical statistics now include 20 attendance rows belonging to inactive students. The temporary synthetic admin was removed and the real-copy app/validation services remain stopped. Secure dump and aggregate evidence remains Git-ignored under `dev/backups/` with owner-only permissions.

## Enhancement workflow

1. Keep the as-is baseline tests passing.
2. Add the academic-year/enrollment migration and its regression tests.
3. Prove the migration repeatedly against synthetic data.
4. Rehearse against the separately authorized production copy and verify historical and current reports.
5. Only after explicit production approval, prepare a fresh production backup and a separate production migration runbook.

These development scripts do not provide a production-apply command.
