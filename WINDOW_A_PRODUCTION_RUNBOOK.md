# Window A production migration runbook

## Scope and non-negotiable limits

Window A consists only of:

1. Academic-year and enrollment schema, foreign keys, and indexes.
2. Assignment of every existing section to `2025-2026`.
3. One legacy enrollment per existing student in `2025-2026`, preserving inactive students as `retirado`.
4. Backfill of every existing attendance row to the enrollment for the same student and original section.
5. Independent read-only verification.

Window A does **not** promote or graduate students, create `2026-2027` sections or enrollments, reassign teachers, or activate another period. `2026-2027` is created only as a planned, non-current year. Keep `ENABLE_ACADEMIC_PERIOD_ADMIN` unset or `0` throughout.

Use only `window_a_migration.py` for this migration. Do not substitute `migrations/add_academic_year_enrollment.sql`, `dev/enhance_academic_year.py`, `python app.py`, `db.create_all()`, or an ad-hoc SQL session. The runner does not create backups, restore backups, or perform destructive recovery.

MariaDB DDL implicitly commits. A failed apply can therefore leave a partially migrated database even if the runner rolls back pending DML. The write freeze must remain in force after any failure, and recovery must use the separately verified backup procedure below. Never assume that rollback undid DDL.

## Runner modes and safety guards

The runner reads a complete `DATABASE_URL` directly from the process environment. It does not load `.env`, import the Flask application, use fallback credentials, or print the URL, username, password, SQL values, or row data. Do not enable shell tracing (`set -x`), print the environment, or paste the URL into a command line, ticket, or log.

Inject the URL without echoing it in each controlled migration shell:

```bash
read -rsp 'DATABASE_URL (input hidden): ' DATABASE_URL && export DATABASE_URL && printf '\n'
```

The URL must use `mysql+pymysql`, and explicitly contain its host, database, username, and non-empty password. Use a dedicated migration account with only the privileges required for the selected mode. Use a read-only account for independent verification where practical.

| Mode | Command | Behavior |
|---|---|---|
| Default preflight | `PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py` | Read-only consistent snapshot; accepts only a valid legacy baseline or a completely migrated valid state |
| Independent verify | `PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py --verify` | New read-only connection; requires and validates the complete final state |
| Apply | Add `--apply` and every confirmation below | Applies only after all guards pass; a valid complete state is a read-only no-op |

Every apply requires all of these on the same command:

```text
--apply
--confirm-database EXACT_DATABASE_NAME
--confirm-release
--confirm-backup
--confirm-write-freeze
```

The confirmations mean:

- `--confirm-database`: the value exactly equals the database parsed from `DATABASE_URL`.
- `--confirm-release`: the change/release record is approved and names the single compatible application artifact to deploy.
- `--confirm-backup`: a fresh full consistent backup exists and its isolated restore has been verified.
- `--confirm-write-freeze`: every application worker and every other writer is stopped, not merely assumed idle.

Environment authorization is additionally required:

| Target | Required environment |
|---|---|
| Local rehearsal | `APP_ENV=development` or `testing`; local host; database exactly `control_asistencias_dev` or `control_asistencias_test`; `WINDOW_A_REHEARSAL_AUTHORIZATION=APPLY_WINDOW_A_DEVELOPMENT` or `APPLY_WINDOW_A_TESTING`, matching `APP_ENV` |
| Production | `APP_ENV=production` and `WINDOW_A_PRODUCTION_AUTHORIZATION=APPLY_WINDOW_A_PRODUCTION` |

Production has a separate authorization variable deliberately. Rehearsal authorization cannot authorize production. Forced-failure options are rejected in production.

Expected successful statuses are `legacy_ready`, `migrated_valid`, `migrated_verified`, `verified`, or `already_migrated_noop`. Any refusal, unexpected count, partial-object message, or verification error is a stop condition. Do not bypass it with `INSERT IGNORE`, `IF NOT EXISTS`, disabled foreign-key checks, manual reverse DDL, or repeated apply attempts.

## Exact production sequence

### 1. Record approvals and stop every writer

1. Record the release ID, exact production database name, migration operator, independent verifier, approved application artifact, maintenance window, and secure backup location.
2. Confirm that the reviewed application artifact contains the academic-year/enrollment-compatible models and routes. It must be the only application version deployed after the migration.
3. Disable incoming writes at the proxy or service level.
4. Stop **all** old Gunicorn workers. Also stop development servers, cron jobs, queues, Excel imports, attendance writers, student edits/imports, observation writers, teacher-assignment jobs, synchronization jobs, administrative period jobs, and ad-hoc writer sessions.
5. Confirm that no old worker remains running. Old and new workers must never be mixed: their schema assumptions and attendance-enrollment behavior differ.
6. Keep the freeze active through backup, production apply, independent verification, deployment, and read-only smoke checks.

Do not continue if an unidentified writer remains. An advisory lock in the runner prevents concurrent runners; it does not replace this external write freeze.

### 2. Take a fresh full consistent backup

Use the approved backup account and secure storage outside the repository. The following example keeps the password off the command line; do not echo or commit any value.

```bash
umask 077
read -rp 'Production database name: ' PROD_DB_NAME
read -rp 'Production database host: ' DB_HOST
read -rp 'Backup database user: ' DB_USER
read -rsp 'Backup database password: ' MYSQL_PWD && export MYSQL_PWD && printf '\n'
read -rp 'Secure backup directory outside the repository: ' BACKUP_DIR
install -d -m 700 "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/window_a_$(date -u +%Y%m%dT%H%M%SZ).sql"

mariadb-dump \
  --host="$DB_HOST" \
  --port="${DB_PORT:-3306}" \
  --user="$DB_USER" \
  --single-transaction \
  --quick \
  --hex-blob \
  --routines \
  --triggers \
  --events \
  --default-character-set=utf8mb4 \
  "$PROD_DB_NAME" > "$BACKUP"

test -s "$BACKUP"
if grep -Eiq '^[[:space:]]*(CREATE[[:space:]]+DATABASE|USE[[:space:]]+)' "$BACKUP"; then
  printf 'Refusing a dump with database-selection directives\n' >&2
  exit 1
fi
sha256sum "$BACKUP" > "$BACKUP.sha256"
chmod 600 "$BACKUP" "$BACKUP.sha256"
unset MYSQL_PWD
```

This is a full schema-and-data backup with routines, triggers, and events. `--single-transaction` supplies a consistent InnoDB snapshot; the external write freeze is still required and covers non-transactional writers. Record the backup path and digest in the secure release record, not in public logs.

### 3. Verify an isolated restore

Restore only into the isolated development database. Never restore this dump into production as a “verification.” Stop every rehearsal application writer before replacing its database. The existing script replaces only `control_asistencias_dev` in the development container and rejects dumps containing database-selection directives.

```bash
docker compose -f compose.dev.yaml stop app validation
bash dev/scripts/restore_dev_dump.sh "$BACKUP"
```

On the restored copy, independently verify:

- The restore completed without errors and the backup digest still matches.
- Base tables, views, routines, triggers, and events are present with the expected definitions.
- Row counts for every table equal the source counts captured by the backup procedure.
- Students, sections, attendance, observations, teacher assignments, and relevant legacy tables are readable.
- Inactive students and their attendance are present; do not verify only active students.

Run the runner’s read-only preflight against the restored copy. Its `DATABASE_URL` must point to local `control_asistencias_dev`; do not reuse the production URL.

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py
```

It must report `legacy_ready` before the first rehearsal. A `migrated_valid` result means the source was not the expected legacy baseline; stop and reconcile the release assumptions rather than forcing a migration.

### 4. Rehearse Window A and verify it independently

Use only the isolated local URL. Stop all writers to the rehearsal database as well.

```bash
APP_ENV=development \
WINDOW_A_REHEARSAL_AUTHORIZATION=APPLY_WINDOW_A_DEVELOPMENT \
ENABLE_ACADEMIC_PERIOD_ADMIN=0 \
PYTHONDONTWRITEBYTECODE=1 \
venv/bin/python window_a_migration.py \
  --apply \
  --confirm-database control_asistencias_dev \
  --confirm-release \
  --confirm-backup \
  --confirm-write-freeze
```

Require `migrated_verified`. Then use a new shell or a new connection and the local read-only URL:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py --verify
```

Require `verified`. Review aggregate counts and the independent SQL checks in section 6. Confirm that student pointers and active flags, section payloads, attendance payloads, observations, teacher assignments, and legacy counts did not change. Confirm that inactive students have preserved attendance and `retirado` legacy enrollments, not promoted/graduated outcomes.

### 5. Prove forced-failure recovery before touching production

Repeat this drill against the isolated copy, never against production:

1. Restore the same verified backup again to `control_asistencias_dev` with `dev/scripts/restore_dev_dump.sh`.
2. Reconfirm the local write freeze and run the rehearsal apply with a deliberate failure after a committed DDL step:

   ```bash
   APP_ENV=development \
   WINDOW_A_REHEARSAL_AUTHORIZATION=APPLY_WINDOW_A_DEVELOPMENT \
   ENABLE_ACADEMIC_PERIOD_ADMIN=0 \
   PYTHONDONTWRITEBYTECODE=1 \
   venv/bin/python window_a_migration.py \
     --apply \
     --confirm-database control_asistencias_dev \
     --confirm-release \
     --confirm-backup \
     --confirm-write-freeze \
     --rehearsal-fail-after set_seccion_year_not_null
   ```

3. Require a nonzero exit and the implicit-DDL recovery warning. Do not attempt reverse DDL or a second apply.
4. Run read-only preflight and require rejection of the partial state.
5. Recover only by restoring the verified backup through the isolated restore procedure.
6. Run preflight and require `legacy_ready`; repeat the normal rehearsal apply and independent verification to prove the recovered copy is usable.

If any part of this drill fails, production apply is not authorized. Resolve the backup/restore problem first.

### 6. Run production preflight and apply

Reconfirm that production writers are still stopped, the release is approved, the backup is fresh and restore-tested, and `ENABLE_ACADEMIC_PERIOD_ADMIN` is unset or `0`. Inject the production `DATABASE_URL` securely.

Run default read-only preflight:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py
```

Require `legacy_ready` for the initial migration. If it reports `migrated_valid`, do not claim a new migration occurred; establish who performed it and use only the no-op/verification path after reviewing the release record. Any partial or unexpected state is a recovery decision, not an apply opportunity.

Apply with the exact approved production database name:

```bash
APP_ENV=production \
WINDOW_A_PRODUCTION_AUTHORIZATION=APPLY_WINDOW_A_PRODUCTION \
ENABLE_ACADEMIC_PERIOD_ADMIN=0 \
PYTHONDONTWRITEBYTECODE=1 \
venv/bin/python window_a_migration.py \
  --apply \
  --confirm-database "$PROD_DB_NAME" \
  --confirm-release \
  --confirm-backup \
  --confirm-write-freeze
```

Require `migrated_verified` (or `already_migrated_noop` only for an intentionally pre-migrated target). The runner rechecks the baseline immediately before writing, validates backfill before the final DDL, uses no conflict-hiding SQL, and opens an independent read-only connection for final verification. It compares immutable row snapshots and SHA-256 digests without printing row contents.

If apply fails:

1. Keep every writer stopped and do not deploy either application version.
2. Do not rerun, drop objects, reverse links, or assume DML rollback restored the schema.
3. Preserve the failure output and database state for inspection; the runner’s messages are designed not to contain credentials or row data.
4. Follow the approved external recovery procedure using the verified pre-migration backup.
5. Verify the recovery independently before considering another maintenance attempt.

If validation fails after new writes have been released, do **not** blindly restore over those writes. Escalate for controlled recovery.

### 7. Independently verify the production database

Use a separate shell, a separate read-only database connection, and preferably a separately provisioned read-only account. Do not reuse the apply connection.

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python window_a_migration.py --verify
```

Require `verified`. Then have the independent verifier run equivalent aggregate and metadata queries through a separate MariaDB client. The following SQL contains no row-level student output:

```sql
SELECT nombre, codigo, fecha_inicio, fecha_fin, es_actual
FROM anio_escolar
ORDER BY nombre;

SELECT
  (SELECT COUNT(*) FROM estudiante) AS students,
  (SELECT COUNT(*) FROM estudiante WHERE activo = 0) AS inactive_students,
  (SELECT COUNT(*) FROM seccion) AS sections,
  (SELECT COUNT(*) FROM inscripcion) AS enrollments,
  (SELECT COUNT(*) FROM asistencia_estudiante) AS attendance;

SELECT
  (SELECT COUNT(*) FROM seccion s
    JOIN anio_escolar y ON y.id_anio_escolar = s.id_anio_escolar
    WHERE y.nombre = '2026-2027') AS target_sections,
  (SELECT COUNT(*) FROM inscripcion i
    JOIN anio_escolar y ON y.id_anio_escolar = i.id_anio_escolar
    WHERE y.nombre = '2026-2027') AS target_enrollments,
  (SELECT COUNT(*) FROM inscripcion
    WHERE estado IN ('promovido', 'graduado')) AS promoted_or_graduated,
  (SELECT COUNT(*) FROM anio_escolar WHERE es_actual = 1) AS current_years,
  (SELECT COUNT(*) FROM asistencia_estudiante
    WHERE fecha < '2025-09-01' OR fecha > '2026-08-31'
      OR fecha IS NULL OR id_inscripcion IS NULL) AS invalid_attendance;

SELECT COUNT(*) AS invalid_attendance_links
FROM asistencia_estudiante a
LEFT JOIN inscripcion i ON i.id_inscripcion = a.id_inscripcion
LEFT JOIN estudiante e ON e.id_estudiante = a.id_estudiante
LEFT JOIN anio_escolar y ON y.id_anio_escolar = i.id_anio_escolar
WHERE i.id_inscripcion IS NULL
   OR e.id_estudiante IS NULL
   OR y.id_anio_escolar IS NULL
   OR i.id_estudiante <> a.id_estudiante
   OR i.id_seccion <> e.id_seccion
   OR y.nombre <> '2025-2026';

SELECT COUNT(*) AS invalid_enrollments
FROM inscripcion i
LEFT JOIN estudiante e ON e.id_estudiante = i.id_estudiante
LEFT JOIN seccion s ON s.id_seccion = i.id_seccion
LEFT JOIN anio_escolar y ON y.id_anio_escolar = i.id_anio_escolar
WHERE e.id_estudiante IS NULL
   OR s.id_seccion IS NULL
   OR y.id_anio_escolar IS NULL
   OR y.nombre <> '2025-2026'
   OR s.id_anio_escolar <> i.id_anio_escolar
   OR i.id_seccion <> e.id_seccion
   OR (e.activo = 1 AND i.estado <> 'activo')
   OR (e.activo = 0 AND i.estado <> 'retirado')
   OR i.origen IS NULL
   OR i.origen <> 'legacy';

SELECT COUNT(*) AS duplicate_current_enrollments
FROM (
  SELECT i.id_estudiante
  FROM inscripcion i
  JOIN anio_escolar y ON y.id_anio_escolar = i.id_anio_escolar
  WHERE y.nombre = '2025-2026'
  GROUP BY i.id_estudiante
  HAVING COUNT(*) > 1
) duplicates;

SELECT COUNT(*) AS missing_current_enrollments
FROM estudiante e
LEFT JOIN (
  SELECT i.id_inscripcion, i.id_estudiante
  FROM inscripcion i
  JOIN anio_escolar y ON y.id_anio_escolar = i.id_anio_escolar
  WHERE y.nombre = '2025-2026'
) i ON i.id_estudiante = e.id_estudiante
WHERE i.id_inscripcion IS NULL;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND CONSTRAINT_NAME IN (
    'unique_anio_escolar_nombre',
    'unique_anio_escolar_codigo',
    'unique_inscripcion_estudiante_anio',
    'unique_inscripcion_estudiante',
    'unique_seccion_anio_grado_nombre',
    'fk_inscripcion_estudiante',
    'fk_inscripcion_seccion',
    'fk_inscripcion_anio',
    'fk_seccion_anio',
    'fk_asistencia_inscripcion_estudiante'
  )
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND INDEX_NAME IN (
    'unique_anio_escolar_nombre',
    'unique_anio_escolar_codigo',
    'unique_inscripcion_estudiante_anio',
    'unique_inscripcion_estudiante',
    'idx_inscripcion_anio_seccion_estado',
    'idx_inscripcion_seccion',
    'unique_seccion_anio_grado_nombre',
    'idx_asistencia_inscripcion'
  )
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION,
       k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME,
       r.UPDATE_RULE, r.DELETE_RULE
FROM information_schema.KEY_COLUMN_USAGE k
JOIN information_schema.REFERENTIAL_CONSTRAINTS r
  ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
 AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
 AND r.TABLE_NAME = k.TABLE_NAME
WHERE k.CONSTRAINT_SCHEMA = DATABASE()
  AND k.CONSTRAINT_NAME IN (
    'fk_inscripcion_estudiante',
    'fk_inscripcion_seccion',
    'fk_inscripcion_anio',
    'fk_seccion_anio',
    'fk_asistencia_inscripcion_estudiante'
  )
ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION;
```

Acceptance criteria:

- Exactly `2025-2026` (`2526`, current) and `2026-2027` (`2627`, not current) exist, with the approved dates; there is exactly one current year.
- Target sections, target enrollments, promoted/graduated results, invalid attendance, invalid links, invalid enrollments, duplicates, and missing enrollments are all zero.
- Enrollment count equals student count, including inactive students.
- Every constraint and index matches the runner’s required column order, uniqueness, referenced columns, and `RESTRICT` rules. Names alone are insufficient.
- Final counts and historical samples reconcile with the verified backup, including inactive students. Investigate expected reporting changes below rather than treating them as data loss.

Do not deploy if any independent check fails.

### 8. Deploy only the new compatible application with Gunicorn

1. Confirm again that no old worker is alive.
2. Deploy the single reviewed artifact identified in the release record. Do not mix old and new code, processes, or worker generations.
3. Keep authorization variables out of the application service. Keep `ENABLE_ACADEMIC_PERIOD_ADMIN` unset or `0`.
4. Start the service through its approved service manager using Gunicorn and `app:app`. For example, the service command may be:

   ```bash
   APP_ENV=production ENABLE_ACADEMIC_PERIOD_ADMIN=0 \
   gunicorn --bind "$GUNICORN_BIND" --workers "$GUNICORN_WORKERS" --timeout 120 app:app
   ```

   `GUNICORN_BIND` and worker count must come from the approved existing service configuration. Use the service manager rather than leaving an unmanaged foreground process.

Never deploy with `python app.py`. Never call `db.create_all()` as a deployment or migration step. Do not start legacy Flask development servers.

### 9. Perform read-only smoke checks while writes remain blocked

Use HTTP `GET` only. Do not submit login forms, attendance forms, imports, or administrative POST/PUT/DELETE requests. Use an existing authenticated session where authenticated pages must be checked.

At minimum:

- `GET /auth/login` renders successfully.
- `GET /secciones` and `GET /api/matriculas` return only current `2025-2026` sections and expected enrollment counts.
- Historical attendance logs and statistics return the same original sections, dates, blocks, presence values, and observation payloads as the pre-migration baseline.
- Teacher assignment views show the original assignments and no target-year reassignment.
- Current roster views handle inactive students as intended; historical reports still include their attendance.
- `/admin/periodos` remains non-mutating and period administration is disabled. Do not attempt activation as a smoke test.

Any write attempt during this stage invalidates the smoke-check boundary. Stop and account for it before continuing.

### 10. Hard operational gate before releasing writes

The release owner and attendance owner must explicitly confirm both statements:

- **No attendance dated `2026-09-01` or later needs to be written before Window B is complete and independently verified.**
- **No promotion, graduation, target-year section/enrollment creation, teacher reassignment, or period activation is needed before Window B.**

With only Window A complete, `2026-2027` has no sections or enrollments, so attendance dated `2026-09-01` or later cannot work. Do not release writes if such attendance is needed. Never change the attendance date, select the current year merely to bypass an error, or silently attribute target-year attendance to `2025-2026`.

Record the explicit confirmations in the release record. If either confirmation cannot be made, keep writes frozen and schedule Window B as a separately reviewed migration; Window A must not be stretched to perform Window B work.

Only after both confirmations, successful read-only smoke checks, and independent database verification:

1. Reconfirm that only the new Gunicorn workers are running.
2. Reconfirm `ENABLE_ACADEMIC_PERIOD_ADMIN` is unset or `0`.
3. Re-enable ordinary `2025-2026` writes at the proxy/service level.
4. Restart approved ordinary writers deliberately; do not restart old application workers or period-activation jobs.
5. Monitor for rejected out-of-window attendance and treat it as the expected Window A boundary, not as permission to reattribute data.

## Reporting differences and inactive-student review

Some reporting differences are expected because the compatible application derives historical attendance from its enrollment and original year-specific section instead of the student’s mutable current-section pointer. Historical reports can also include inactive students that old active-only joins omitted. Current roster and current enrollment counts can therefore differ from historical totals without indicating loss or duplication.

Before accepting the release, compare representative active and inactive students across current rosters, historical logs, and statistics. Verify that inactive students remain unchanged, retain their original attendance and section attribution, and have `retirado` legacy enrollments. Do not “correct” expected historical-count differences by changing attendance links, student pointers, active flags, or enrollment outcomes.

## Completion evidence

Retain in the secure release record:

- Release ID, exact database name, operator/verifier approvals, and timestamps.
- Backup location, SHA-256, routines/triggers/events confirmation, isolated-restore evidence, and forced-failure recovery evidence.
- Preflight, apply, and independent-verify statuses with aggregate counts only.
- Independent metadata-definition and invariant query results.
- Gunicorn artifact/process verification and read-only smoke results.
- Explicit Window B attendance gate confirmations and the identities of the release/attendance owners.

Do not store `DATABASE_URL`, passwords, production dumps, row-level student data, or attendance/observation payloads in the release ticket or repository.
