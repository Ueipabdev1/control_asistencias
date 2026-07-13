# Audit — Offboarding: Daniel Bongianni

**App:** control_asistencias (`/control_asistencias/`, port 5006)
**Date:** 2026-07-13
**Performed by:** Gustavo Perdomo (gustavo.perdomo@ueipab.edu.ve) — administrador
**Reason:** User no longer works with the organization. Access revocation + audit record prior to password rotation.

## Subject
| Field | Value |
|---|---|
| Name | Daniel Bongianni |
| Email | daniel.bongianni@ueipab.edu.ve |
| `id_usuario` | 2 |
| Role | profesor |
| Linux/OS account | `dbongianni` (owns app source on disk; handled separately) |

## Access footprint found (authoritative = DB record ownership; no auth log exists)
- Section assignments (`profesor_seccion`): 2 → `id_seccion` 6 and 14 ("Única").
- Attendance authored (`asistencia_estudiante`): 132 records, 2026-03-05 → 2026-06-18.
- Observations authored (`observacion_seccion`): 1 record, 2026-03-12.
- Last data-writing activity: **2026-06-18**.
- Note: nginx logs record IPs/URLs only (no in-app username); neither Flask app nor gunicorn writes an auth log. No `last_login` column exists on `usuario`.

## Action taken — account disabled
```sql
-- BEFORE: activo = 1
UPDATE usuario SET activo = 0 WHERE id_usuario = 2;
-- AFTER:  activo = 0  (verified)
```
Historical records authored by this user are **retained** (not deleted) for audit integrity; only login access was revoked.

## Follow-up (tracked separately)
- [ ] Rotate shared/generic admin password: `admin@ueipab.edu.ve`.
- [ ] Rotate app secrets exposed to former user's filesystem access (`SECRET_KEY`, DB credentials in `.env`).
- [ ] Lock OS account `dbongianni` and review `webdev` group membership (write access to prod code).
