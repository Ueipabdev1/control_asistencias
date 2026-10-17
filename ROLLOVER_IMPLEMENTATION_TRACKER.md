# Academic-Year Enhancement and Rollover Tracker

**Purpose:** Track the database enhancement, application changes, migration rehearsals, and eventual next-grade rollover without risking production data or historical attendance attribution.

**Current phase:** Window A synthetic rehearsal complete — authorized production-copy rehearsal pending
**Production status:** Untouched
**Development environment:** Ready
**Full production-data rehearsal:** Not performed

Related documents:

- `NEXT_GRADE_ROLLOVER.md` — detailed migration design, constraints, and rollback requirements.
- `WINDOW_A_PRODUCTION_RUNBOOK.md` — dedicated Window A preflight, apply, verification, backup, recovery, and deployment runbook.
- `dev/README.md` — isolated development/test environment instructions.

## Safety baseline

Current configured production database, verified after creating the development environment:

- 227 students: 224 active and 3 inactive.
- 39,009 individual attendance rows.
- 1,253 section observations.
- 84 teacher-section assignments.
- 15 current sections.
- 11 active fifth-year students to archive as graduates, with 3,025 attendance rows to preserve.

No production schema or data changes have been made.

## Implementation roadmap

| Phase | Work | Exit criteria | Status |
|---|---|---|---|
| 1. Development environment | Create isolated MariaDB 11.8 and Python 3.11 stack, as-is schema baseline, synthetic data, safety guards, and automated tests | Isolated environment verified; production counts unchanged | **Done** |
| 2. Confirm rollover rules | Finalize the cutoff, full promotion map, final section rosters, and roster exceptions | Approved source-to-target mapping with exactly one destination per eligible student and no unresolved section assignments | **In progress** |
| 3. Schema migration in dev | Add academic years, enrollments, year-specific sections, and attendance-to-enrollment relationship | Migration applies cleanly to the as-is development schema without deleting existing records | **Done** |
| 4. Historical backfill in dev | Enroll existing students in the current academic year and link existing attendance to the correct enrollment | Every attendance row retains its original student, section, and academic year; no orphaned rows | **Done** |
| 5. Application compatibility | Update attendance writes, logs, statistics, section lists, teacher views, enrollment counts, and Excel import | Current operations work with the new model; historical queries no longer rely on current section or active status | **Done** |
| 6. Automated regression tests | Test promotions, fourth-year A/B mapping, graduation archiving, historical attribution, imports, structure/period administration, real-extraction mapping, authorization, attendance policy, and Window A migration guards | 94 tests passing; no duplicate promotion, missing student, deleted history, changed historical attribution, or unsafe Window A state transition | **Done** |
| 7. Full production-copy rehearsal | Restore an authorized current dump into `control_asistencias_dev`, capture baseline aggregates, run the complete migration, and compare results | All students mapped; all attendance and observations preserved; historical reports match before/after | Pending |
| 8. Production runbook and approval | Document commands, maintenance window, fresh backup, write freeze, validation, and rollback | Window A runbook drafted and synthetically rehearsed; clean release and explicit production execution readiness still pending | **In progress** |
| 9. Production schema enhancement | Add the new structure and backfill history without promoting anyone | Enhanced application and historical reports validated; original student pointers and attendance payloads unchanged; no student movement | Pending |
| 10. Production rollover | In one controlled DML transaction, archive graduates, promote students, create the approved sections, and apply assignments | Approved mappings applied; 11 graduates archived; split totals conserved; all assertions pass | Pending |
| 11. Post-rollover verification | Test attendance, rosters, statistics, observations, teacher access, imports, and historical reports | Current operations work and historical attribution remains correct | Pending |
| 12. Closeout | Record final counts, validation evidence, backup references, and follow-up work | Tracking documents complete and recovery information retained | Pending |

## Phase 2 decisions required

- [x] Confirm the academic-year labels: current `2025-2026`, target `2026-2027`.
- [ ] Confirm the exact rollover cutoff date and that only currently active, explicitly approved students are promoted.
- [ ] Approve the complete source-section to target-section promotion map, including maternal-to-primary and primary-to-secondary transitions.
- [x] Resolve the proposed first-year split: the synthetic 2026-2027 design keeps first, second, third, and fifth year single-section; only fourth year has A/B.
- [ ] Approve the final per-student fourth-year A/B roster and target sections for current sixth-grade primary, first-year secondary, and second-year secondary students.
- [ ] Reconcile the three Excel students currently inactive in the database.
- [ ] Reconcile the two active database students absent from the latest Excel roster.
- [x] Use teacher assignments from the latest Kampus publication and Odoo teaching calendars, matched by `work_email`, rather than automatically following cohorts.
- [x] Confirm the working secondary map: current fourth-year Única promotes to fifth year, and current fifth year graduates.

## Intended secondary-school rollover

| Current cohort | Intended destination | Approval |
|---|---|---|
| 1er año Única | 2do año; single-section working design | Final production roster pending |
| 2do año Única | 3er año; single-section working design | Final production roster pending |
| 3er año A | 4to año A | Confirmed in synthetic; final production map pending |
| 3er año B | 4to año B | Confirmed in synthetic; final production map pending |
| 4to año Única | 5to año; single-section working design | Confirmed in synthetic; final production map pending |
| 5to año Única | Graduated archive; no active next-year enrollment | Confirmed in synthetic; final production map pending |

Historical sections, including `1er año Única`, must not be renamed or deleted. New academic-year sections receive new IDs.

## Analysis inputs and development artifacts

- Academic periods confirmed by the user: current `2025-2026`, target `2026-2027`. The exact rollover cutoff remains pending.
- Odoo/Kampus analysis and the confirmed synthetic design keep first, second, third, and fifth years single-section; only 4to año is split A/B. There is no first-year split in the 2026-2027 synthetic rollover.
- Current 3er año A/B maps to 4to año A/B; current 4to año promotes to 5to; current 5to año graduates.
- Teacher assignments should come from the latest Kampus publication and Odoo teaching calendars, matched by `work_email`, rather than automatically following cohorts.
- [x] Built the minimal migration-packet contract and deterministic synthetic 2026-2027 packet (`dev/migration_packet.py`, `dev/build_synthetic_packet.py`).
- [x] Verified 24 automated tests passing, including duplicate identity, unknown section, teacher ambiguity, unexpected-column, and manifest-hash negative controls.
- [x] Built the academic-year/enrollment schema migration using the validated packet contract.
- [x] Backfilled 2025-2026 enrollments and linked every historical attendance row to its original enrollment.
- [x] Applied the synthetic 2026-2027 rollover: 28 promoted students, 2 archived graduates, 15 new year-specific sections, and all 90 attendance links preserved.
- [x] Updated current-section APIs, student CRUD, Excel import, attendance writes, logs, and statistics for enrollment history.
- [x] Verified 33 automated tests passing and added the admin validation page.
- [x] Published the isolated validation site at `https://dev.ueipab.edu.ve/control_asistencias_enhance/` and verified login, sections, historical statistics, and a real attendance write.
- [x] Added the admin structure manager at `/admin/estructura`: grade and current-year section management, duplicate protection, no deletes, and no historical rewrites. Verified the public create/rename/deactivate flow.
- [x] Added **Estructura académica** to the admin-only main sidebar and verified the public navigation flow. Professors do not see the entry; 39 automated tests pass.
- [x] Added **Períodos académicos** at `/admin/periodos`: historical/current/planned views, guarded planned-period creation, packet preflight, CSRF protection, typed confirmation, and atomic browser-driven activation. Verified 46 automated tests and the public 2025-2026 → 2026-2027 activation with all 90 attendance links preserved.
- [x] Performed the authorized minimal real-data extraction with read-only application/Odoo/Google sources and offline/cache-only Akdemia/Kampus inputs. The ignored draft contains 224 students (213 continuing and 11 graduates), 15 sections, and 86 teacher assignments; all real files have owner-only permissions.
- [x] Applied the Odoo enrollment-journey authority model: 183 students now validate directly through Odoo, and secondary Akdemia/Excel disagreements are warnings only when identity, journey state, name, graduation status, and target grade agree.
- [x] Added authentication, administrator-API, registration, inactive-session, and current V2 professor-section protections; legacy V1 section-ID authorization remains a documented separate review.
- [x] Added planned-period and retired-enrollment attendance write guards, plus the dedicated Window A runner and `WINDOW_A_PRODUCTION_RUNBOOK.md`.
- [x] Passed 94 automated tests and a live synthetic Window A rehearsal: apply, independent verify, no-op rerun, forced partial-DDL detection, recovery reset, reapply, and HTTP smoke checks.
- [ ] Resolve the remaining 47 student review rows and 30 teacher-group pairs blocked by unmatched local emails for Window B; detailed identities remain only in the ignored secure reconciliation.
- [ ] Perform the authorized Window A production-copy rehearsal; this schema/app track does not require the Window B packet to be strict-ready.
- [ ] Perform the complete production-copy rollover rehearsal after the real packet passes strict validation and before Window B.

## Production safety gates

Do not authorize the production rollover until all of these are checked:

- [ ] All Phase 2 decisions are resolved and recorded.
- [x] Synthetic migration and regression tests pass repeatedly.
- [ ] A separately authorized current production copy has been restored into the development container.
- [ ] Full-data rehearsal passes with no missing students or changed historical reports.
- [ ] Every production attendance row remains linked to its original enrollment after the rehearsal.
- [ ] Every eligible student has exactly one approved next-year destination or a graduated result.
- [ ] A fresh production backup and verified restoration procedure are ready.
- [ ] A maintenance write freeze and explicit production authorization are recorded.

## Window A production-readiness gates

Window A is limited to schema, 2025-2026 backfill, compatible application deployment, and verification. It does not activate 2026-2027 or move any student. The user selected this track on 2026-10-17; production execution remains blocked by these gates:

- [x] Complete the required authentication, administrator-API, inactive-account, registration, and current V2 professor-section security fixes.
- [x] Complete a dedicated production runner with read-only preflight, explicit apply authorization, partial-state rejection, and independent verification. The destructive development-database guard remains unchanged.
- [x] Prove the runner against synthetic MariaDB, including forced partial-DDL detection, recovery, no-op rerun, and HTTP smoke checks; 94 automated tests pass.
- [ ] Pin a clean reviewed release containing the compatible application, security fixes, runner, tests, and runbook.
- [ ] Rehearse Window A and forced-failure recovery against an authorized current production copy in the isolated environment.
- [ ] Prepare a fresh full backup, isolated restore verification, write freeze, old-worker shutdown, and combined database/application recovery procedure.
- [ ] Confirm that no attendance dated 2026-09-01 or later must be recorded before Window B. Window A intentionally creates no target-year enrollments, and the enhanced app now rejects planned-period writes rather than reattributing them.
- [ ] Verify expected application/report differences against real data, including inactive-student behavior and enrollment-based section counts.

Read-only evidence on 2026-10-17 found zero attendance rows dated 2026-09-01 or later and a latest attendance write of 2026-07-17. This supports rehearsal but does not remove the operational go/no-go confirmation before production writes are reopened.

## Commands for development verification

```bash
# Build, reset, test, and start the isolated environment
bash dev/scripts/bootstrap.sh

# Run automated tests
bash dev/scripts/test.sh

# Reset development to the as-is schema plus synthetic data
bash dev/scripts/reset_dev.sh
```

Development app: `http://127.0.0.1:5017`
Synthetic login: `admin@dev.test` / `dev-only`

## Execution log

| Date | Environment | Action | Result | Next action |
|---|---|---|---|---|
| 2026-10-16 | Development | Created isolated stack, as-is schema baseline, synthetic data, safety guards, and tests | 13 tests passed; HTTP login and section API verified | Confirm Phase 2 rollover rules |
| 2026-10-16 | Production | Read-only post-setup count verification | Unchanged: 227 students and 39,009 attendance rows | No production action authorized |
| 2026-10-16 | Development | Academic-year schema, backfill, synthetic rollover, application compatibility, and validation site | 33 tests passed; public validation flow verified including attendance write | Complete structure administration and navigation |
| 2026-10-16 | Development | Added structure manager and admin-only main-menu link | 39 tests passed; public manager and navigation flows verified | Add academic-period administration |
| 2026-10-16 | Development | Added guarded academic-period manager and completed public browser activation | 46 tests passed; 2025-2026 historical and 2026-2027 current; 90 attendance links preserved | Resolve final mapping and authorize real-data extraction |
| 2026-10-16 | Production | Read-only post-validation count verification | Unchanged: 227 students and 39,009 attendance rows | No production action authorized |
| 2026-10-17 | Read-only sources | Generated minimal real draft and aggregate reconciliation | 56 tests passed; 213 continuing, 11 graduates, 58 student reviews, 30 teacher-group pairs blocked; strict readiness blocked | Apply the reviewed source-authority model |
| 2026-10-17 | Read-only sources | Applied Odoo enrollment-journey authority rules | 57 tests passed; 183 students Odoo-authoritative; review rows reduced to 47; strict readiness still blocked | Resolve remaining identity, journey, section, and teacher-email exceptions |
| 2026-10-17 | Production | Read-only post-extraction count verification | Unchanged: 227 students and 39,009 attendance rows | No production action authorized |
| 2026-10-17 | Read-only sources / development | Refreshed extraction and classified the unresolved rows into a secure action file | 57 tests passed; 47 student rows and 9 teacher profiles remain blocked; production counts unchanged; `strict_ready=false` | Resolve the source/account actions in ignored `review_actions.json` |
| 2026-10-17 | Development / synthetic MariaDB | Implemented Window A security and attendance safeguards, dedicated runner, and production runbook; completed live synthetic migration and recovery rehearsal | 94 tests passed; apply/verify/no-op/forced-failure/recovery/reapply and HTTP smoke passed; 30 students and 90 attendance rows preserved; production untouched | Authorize and perform the Window A production-copy rehearsal |

## Current next action

For **Window A**, pin the reviewed release candidate and obtain authorization to restore a current production dump into `control_asistencias_dev`; then follow `WINDOW_A_PRODUCTION_RUNBOOK.md` through the real-data rehearsal, independent verification, and forced-failure recovery before considering production execution. Confirm the operational rule that no attendance dated 2026-09-01 or later will be written before Window B.

For **Window B**, continue the authorized human review in ignored `dev/backups/real_2026_2027/review_actions.json`: 47 student rows and 9 teacher profiles remain unresolved, and the cutoff/final mapping are not approved. The Window B packet remains `strict_ready=false`; no rollover or period activation is authorized.
