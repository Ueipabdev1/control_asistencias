# Next-grade rollover, section split, and graduation archive

**Status:** WINDOW A SYNTHETIC REHEARSAL COMPLETE; WINDOW B MAPPING STILL BLOCKED. The enhancement, synthetic rollover, security safeguards, dedicated Window A runner, and forced-failure recovery drill are implemented and tested in the isolated environment. Production remains unchanged; an authorized production-copy rehearsal and clean release are pending for Window A, while final mapping approval and a strict-ready packet remain pending for Window B.

## Recommendation

Use a history-safe academic-year rollover. A direct in-place update of `estudiante.id_seccion`, renaming section 10, and deactivating fifth-year students would preserve rows at the SQL level but would break the meaning of historical attendance reports.

The safe design is to preserve the current year and its section/enrollment records, create the next year's sections separately, link attendance to the enrollment under which it was recorded, and promote students through an explicit mapping. Never infer A/B assignments from `Grado.orden` or run a chain of grade-by-grade updates.

## Confirmed baseline

Current configured database:

- 227 students: 224 active and 3 inactive.
- 39,009 individual attendance rows, dated 2026-03-02 through 2026-07-17.
- 1,253 section observations.
- 84 teacher-section assignments.
- 15 current sections.
- Current fifth year: 11 active students with 3,025 attendance rows.
- Current third year: 15 active students in A and 15 active plus 1 inactive in B.
- Current fourth year: 12 active students in Única.
- Current first year: 26 active plus 1 inactive in Única (section ID 10).

Latest Excel comparison found five roster exceptions to reconcile before rollover:

- Three Excel students are inactive in the database: one each in first year, second year, and third-year B.
- Two active database students are absent from Excel: one in third grade primary and one in first year.
- No student was found in the wrong grade or section, and no duplicate student IDs were found.

Original production implementation constraints identified during the read-only audit:

- `asistencia_estudiante` referenced only the student; it had no section, enrollment, or academic-year snapshot.
- Statistics and attendance logs joined through the student's current section and often excluded inactive students. Moving or deactivating students therefore changed or hid historical results.
- Section observations and teacher assignments reference sections with delete cascades. Students also restrict section deletion. Do not delete sections, grades, students, or attendance during rollover.
- `Matricula` is legacy and points to the old plural `secciones` table. New V2 section IDs must not depend on that table; current V2 enrollment counts are calculated from current enrollments instead.
- The original database had no unique constraint on `(id_grado, nombre_seccion)`, so migration preflight must explicitly detect duplicate target sections.

## Working promotion map

The following is the working map to confirm before production execution. “Assumed” rows follow normal next-grade progression but are not yet an approved data-mapping contract. The synthetic rollover implements single-section first, second, third, and fifth years; only fourth year has A/B.

| Current cohort | Active now | Destination | Status |
|---|---:|---|---|
| Maternal Nivel 1 Única | 3 | Maternal Nivel 2 | Assumed |
| Maternal Nivel 2 Única | 5 | Maternal Nivel 3 | Assumed |
| Maternal Nivel 3 Única | 4 | Primaria 1er grado | Assumed cross-stage promotion |
| Primaria 1er–5to grado | 10, 20, 23, 23, 13 | Next primary grade | Assumed |
| Primaria 6to grado Única | 22 | Secundaria 1er año; single-section working design | Grade assumed; final roster pending |
| Secundaria 1er año Única | 26 | Secundaria 2do año; single-section working design | Working map; final roster pending |
| Secundaria 2do año Única | 22 | Secundaria 3er año; single-section working design | Working map; final roster pending |
| Secundaria 3er año A | 15 | Secundaria 4to año A | Confirmed in synthetic rollover |
| Secundaria 3er año B | 15 | Secundaria 4to año B | Confirmed in synthetic rollover |
| Secundaria 4to año Única | 12 | Secundaria 5to año; single-section working design | Confirmed in synthetic rollover |
| Secundaria 5to año Única | 11 | Graduated archive; no next-year enrollment | Confirmed in synthetic rollover |

### Decisions required before any production data update

1. Confirm the exact cutoff date and whether only currently active, explicitly approved students are promoted. Academic-year labels are confirmed as `2025-2026` and `2026-2027`.
2. Confirm the full source-section to target-section map above, including cross-stage transitions.
3. Approve the final per-student fourth-year A/B roster and the single-section destinations for current sixth-grade primary, first-year secondary, and second-year secondary students. Do not split students arbitrarily by name, ID, or gender.
4. Confirm treatment of the three inactive students and two active students absent from Excel.
5. Obtain explicit authorization for minimal real-data extraction, the full production-copy rehearsal, and later production execution. Teacher assignments will come from the latest Kampus publication and Odoo teaching calendars, matched by `work_email`.

## Implementation plan

### Phase 1 — Tracking, backup, and dry run

- [x] Keep this document as `NEXT_GRADE_ROLLOVER.md` and record decisions, execution timestamps, validation results, and rollback information in it.
- [ ] Reconcile the five roster exceptions and freeze the final roster/mapping; keep personally identifying mapping files out of Git.
- [ ] Take a full database backup and restore it into a separate staging database. Verify the restore before testing the migration.
- [ ] Build a read-only preflight that checks section IDs against expected grade/name labels, detects duplicate student IDs and target sections, and verifies that every promoted student has exactly one destination.
- [ ] Capture pre-rollover aggregates for attendance by enrollment/section/date/block/presence, student counts, observations, and teacher assignments for later comparison.

### Development harness status

- [x] Created an isolated Docker Compose stack with MariaDB 11.8 and Python 3.11; development and test databases are separate from production (`compose.dev.yaml`, `dev/README.md`).
- [x] Captured the current as-is schema without table data (`dev/baseline/current_as_is_schema.sql`) and added deterministic synthetic data with no production personal records.
- [x] Added hard test-target validation and limited pytest collection to `tests/` so older live-database scripts are not run automatically.
- [x] Verified 13 automated tests passing, repeatable development resets, real HTTP login, and `/secciones` returning 15 synthetic sections.
- [x] Confirmed after setup that the configured database still has 227 students and 39,009 attendance rows; no production schema or data changes were made.
- [ ] Perform a full-data rehearsal using a separately authorized current production dump through `dev/scripts/restore_dev_dump.sh`; this has not been done yet.

### Phase 2 — Preserve academic history before moving anybody

- [x] Add an academic-year model and an enrollment model. An enrollment records student, year-specific section, academic year, and status (`activo`, `promovido`, `graduado`, `retirado`, or `inactivo`), with one enrollment per student per academic year.
- [x] Make sections year-specific in development. Backfill the 15 synthetic sections and all synthetic students into the current academic year; create next-year sections with new IDs rather than renaming historical sections.
- [x] Add an enrollment foreign key to `asistencia_estudiante`, initially nullable, and verify the synthetic backfill of all 90 attendance rows. The production backfill of 39,009 rows remains pending the authorized rehearsal.
- [x] Keep `estudiante.id_seccion` temporarily as the current-section pointer for compatibility, synchronized with the current enrollment in the same transaction. Keep `estudiante.activo` for current roster visibility, but stop using it to exclude historical attendance.
- [x] Update `models.py`, the clean schema, and a new migration consistently, including academic year in the section-name uniqueness rule.
- [x] Update attendance writes in `routes_estudiantes.py` to save the correct enrollment for the selected date/section.
- [x] Update historical attendance logs and statistics in `routes.py` and `routes_estadisticas.py` to derive section/year from the attendance enrollment rather than the student's current section, and to include graduated/inactive students in historical results.
- [x] Update current-section lists, teacher views, enrollment counts, views, and Excel matching to use the current academic year and active current sections. Prevent `utils/excel_processor.py` from importing into historical sections.
- [x] Decouple current V2 enrollment counts from legacy `Matricula`; update `sincronizar_matriculas.py` so it cannot insert legacy matrícula rows for new year-specific section IDs.
- [x] Leave legacy V1 attendance tables and endpoints unchanged.

The synthetic implementation of this phase is complete; production execution remains pending. Schema DDL and data backfills must be tested separately because MySQL/MariaDB DDL can implicitly commit; only the final DML rollover should be wrapped in one transaction.

### Phase 3 — Build the new structure and explicit mapping

- [ ] Preserve current section 10 as historical `1er año secundaria / Única`; do not rename it. The synthetic 2026-2027 design has no first-year split; any future structural change requires explicit approval and new year-specific section IDs.
- [ ] Create fourth-year A and B for the next academic year. Map current third-year A to fourth-year A and third-year B to fourth-year B.
- [ ] Create or reuse the other required next-year sections according to the approved full mapping, including fifth-year Única for the current fourth-year cohort.
- [ ] Generate one mapping row per eligible active student from the original frozen enrollment to exactly one next-year enrollment, or to `graduado` for current fifth year. Existing inactive students remain unchanged unless explicitly approved.
- [ ] Generate the A/B assignments from the approved roster/rule and verify that split output totals equal the approved source cohort totals.
- [ ] Prepare next-year teacher assignments without deleting historical assignments; deduplicate by teacher and year-specific section.

### Phase 4 — Rehearse, then execute during a write freeze

- [ ] Run the complete migration and application verification against the restored staging copy first.
- [ ] Schedule a maintenance window and stop attendance, student-import, student-edit, observation, and teacher-assignment writes during the final rollover.
- [ ] Take a fresh production backup immediately before execution and record its location securely.
- [ ] Re-run preflight against production; abort if student counts, section identities, or mapping contents differ from the approved baseline.
- [ ] Execute the final DML in one transaction: close current enrollments with the correct result, archive the 11 graduates without deleting them, create next-year sections/enrollments, update current-section pointers, and create approved teacher assignments.
- [ ] Do not use sequential in-place promotions that could promote the same student twice. Use only the frozen mapping based on original enrollment IDs.
- [ ] Keep all historical attendance, observations, students, sections, and teacher assignments unchanged.
- [ ] Run post-migration assertions before commit; roll back the transaction on any failure.

### Phase 5 — Verification and rollback criteria

Data invariants:

- [ ] Total student IDs, attendance rows, and historical observations equal the frozen pre-rollover baseline; no historical row is deleted or reattributed.
- [ ] Every attendance row points to an enrollment belonging to the same student, and every existing attendance row retains its original section/year.
- [ ] Every active non-graduate has exactly one current-year enrollment; graduates have a `graduado` historical result and no active next-year enrollment.
- [ ] The 11 current fifth-year students are archived, their 3,025 attendance rows remain intact, and historical reports still include them.
- [ ] Current third-year A/B active students land in fourth-year A/B respectively; current fourth-year students land in fifth year if that mapping is approved.
- [ ] A/B split totals conserve every approved source student, with no duplicates or unmapped students.
- [ ] Current active enrollment equals previous active enrollment minus archived graduates plus/minus explicitly approved roster corrections or new intake.
- [ ] No current import or section endpoint returns a historical section; no duplicate current teacher assignment or current enrollment exists.

Application verification on staging and after production release:

- [ ] Compare historical attendance aggregates and logs before/after for all dates, sections, and blocks; investigate every difference.
- [ ] Verify `/secciones`, `/api/matriculas`, student lists/manual student CRUD, attendance verify/save, section observations, professor assignments, dashboard statistics, and Excel import against current-year sections.
- [ ] Verify teachers see only their assigned current-year sections while administrators can still retrieve historical reports.
- [ ] Run the project's existing verification scripts only against staging, since some are live-DB scripts rather than isolated tests; add focused rollover tests for mapping conservation, graduation archiving, historical attribution, and A/B assignment.

Rollback:

- [ ] Before commit, rollback the DML transaction on any failed assertion.
- [ ] After commit but before any new writes, restore the verified pre-rollover backup if validation fails.
- [ ] If new writes have already occurred, do not blindly restore or run reverse updates; preserve those writes and use the frozen mapping/enrollment audit trail for a controlled recovery.

## Decision log

| Decision | Result | Date / notes |
|---|---|---|
| Academic-year labels | Confirmed: `2025-2026` to `2026-2027` | Exact cutoff still pending |
| Full production promotion map | Pending | Real draft extracted; final review required |
| Proposed first-year A/B split | Not included in the synthetic design | Only fourth year has A/B; first, second, third, and fifth remain single-section |
| Final per-student section roster | Pending | 47 student rows carry review reasons in the secure reconciliation |
| Treatment of roster exceptions | Pending | Includes exact-ID, population, section, and teacher-email mismatches |
| Teacher-assignment rollover policy | Confirmed | Latest Kampus/Odoo assignments, matched by `work_email` |
| Synthetic development validation | Complete | 94 automated tests pass; public validation, browser-driven period activation, security safeguards, and live Window A migration/recovery rehearsal verified |
| Real minimal-data extraction | Draft complete; strict not ready | Odoo authority validates 183 students; 47 reviews and 30 teacher-group pairs remain blocked |
| Backup and full production-copy rehearsal | Pending | Window A requires separate dump/restore authorization; Window B additionally requires a strict-ready packet |
| Production execution authorization | Window A track selected; readiness pending | Production remains unchanged; Window B is not authorized |

## Execution log

| Date | Environment | Action | Result / validation | Backup or reference |
|---|---|---|---|---|
| 2026-10-16 | Planning | Created tracking document and read-only impact audit | Complete; no DB changes | `NEXT_GRADE_ROLLOVER.md` |
| 2026-10-16 | Development | Implemented schema/enrollment history, synthetic rollover, compatible application flows, validation site, and structure manager | 39 tests passed; 28 promoted, 2 graduated, 15 target sections, and 90 historical attendance links preserved | `ROLLOVER_IMPLEMENTATION_TRACKER.md` |
| 2026-10-16 | Development | Added guarded academic-period administration and completed browser-driven activation | 46 tests passed; public 2025-2026 → 2026-2027 activation preserved all 90 attendance links | `/admin/periodos` |
| 2026-10-16 | Production | Read-only post-validation count check | Unchanged: 227 students and 39,009 attendance rows | No production action authorized |
| 2026-10-17 | Read-only sources | Extracted minimal real draft and aggregate reconciliation | 213 continuing, 11 graduated, 58 student reviews, 30 teacher-group pairs blocked; structural validation passed, strict readiness blocked | Ignored `dev/backups/real_2026_2027/`; aggregate `dev/reports/real_2026_2027_extraction.json` |
| 2026-10-17 | Read-only sources | Applied Odoo enrollment-journey authority rules | 57 tests passed; 183 students Odoo-authoritative; review rows reduced from 58 to 47; 30 teacher-group pairs still blocked | Aggregate `dev/reports/real_2026_2027_extraction.json` |
| 2026-10-17 | Production | Read-only post-extraction count check | Unchanged: 227 students and 39,009 attendance rows | No production action authorized |
| 2026-10-17 | Development / synthetic MariaDB | Added Window A security/attendance safeguards and dedicated runner; completed migration, no-op, forced-failure, recovery, and HTTP rehearsal | 94 tests passed; all 30 fictional students and 90 attendance rows preserved; 2025-2026 remained current; no target-year movement | `WINDOW_A_PRODUCTION_RUNBOOK.md` |

## Current safety conclusion

A no-delete migration can avoid foreign-key and cascade damage, but a DB-only in-place rollover is **not safe for historical reporting**. The history-safe design and dedicated Window A runner are validated with synthetic data, and the real draft uses Odoo as the conditional academic authority without production writes. Window A production execution remains blocked by a clean pinned release, an authorized real-data backup/restore rehearsal, and the operational attendance-date confirmation. Window B additionally remains blocked by 47 student review rows, 30 unmatched teacher-group pairs, final cutoff/map approval, and a strict-ready packet. Production remains unchanged.
